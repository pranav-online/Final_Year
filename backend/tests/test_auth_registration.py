from io import BytesIO

import pytest
from uuid import uuid4
from fastapi import HTTPException
from pymongo.errors import PyMongoError
from PIL import Image
from starlette.datastructures import Headers, UploadFile

from models.market import CropListing, CropStatus
from models.user import UserRegister
from routes import auth
from routes.disease import detect_disease
from services import disease_service
from services import market_service
from services.market_service import (
    analyze_demand,
    add_crop_listing,
    get_all_regional_supply,
    get_all_market_alerts,
    get_regional_supply,
)


@pytest.mark.asyncio
async def test_register_works_without_database_config(monkeypatch):
    monkeypatch.setattr(auth, "users_collection", None)

    user = UserRegister(
        full_name="Test User",
        email=f"testuser-{uuid4().hex}@example.com",
        password="secret123",
        role="farmer",
        phone="123",
        location="Nairobi",
    )

    result = await auth.register_with_local_store(user)

    assert result["message"] == "User registered successfully"
    assert result["role"] == "farmer"
    assert result["storage"] == "local"

    # ensure the same email is rejected on repeat
    with pytest.raises(Exception):
        await auth.register_with_local_store(user)


@pytest.mark.asyncio
async def test_demand_analysis_returns_fallback_signals_when_market_is_empty(monkeypatch):
    async def fake_load_regional_supply_index(query=None):
        return {}

    monkeypatch.setattr("services.market_service._load_regional_supply_index", fake_load_regional_supply_index)

    result = await analyze_demand("hyderabad")

    assert result["success"] is True
    assert result["region"] == "hyderabad"
    assert result["analysis"]
    assert result["total_alerts"] >= 0
    assert result["crop_analysis"]["rice"]["expected_demand_kg"] > 0
    assert result["crop_analysis"]["rice"]["supply_demand_ratio"] > 0


@pytest.mark.asyncio
async def test_demand_analysis_compares_supply_to_predicted_demand(monkeypatch):
    async def fake_load_regional_supply_index(query=None):
        return {
            "hyderabad": {"rice": 1400},
            "warangal": {"rice": 100},
        }

    async def no_alert_history(signals):
        return None

    monkeypatch.setattr("services.market_service._load_regional_supply_index", fake_load_regional_supply_index)
    monkeypatch.setattr("services.market_service._save_alert_history", no_alert_history)
    monkeypatch.setattr(
        "services.market_service.predict_dynamic_threshold",
        lambda **kwargs: {
            "predicted_threshold_kg": 700,
            "model": "test demand model",
            "season": "kharif",
        },
    )

    result = await analyze_demand("hyderabad", "rice")
    rice = result["crop_analysis"]["rice"]

    assert rice["current_supply_kg"] == 1400
    assert rice["expected_demand_kg"] == 700
    assert rice["supply_demand_ratio"] == 2
    assert rice["market_status"] == "oversupply"
    assert rice["redistribution_options"][0]["region"] == "Warangal"
    assert rice["price_impact"]["price_drop_pct"] > 0


@pytest.mark.asyncio
async def test_regional_supply_uses_labeled_demo_data_when_region_has_no_listings(monkeypatch):
    class EmptyCursor:
        def __aiter__(self):
            return self

        async def __anext__(self):
            raise StopAsyncIteration

    class EmptyMarketCollection:
        def find(self, query):
            return EmptyCursor()

    monkeypatch.setattr("services.market_service.market_collection", EmptyMarketCollection())

    result = await get_regional_supply("Chennai")

    assert result["success"] is True
    assert result["region"] == "chennai"
    assert result["source"] == "demo_estimate"
    assert result["is_demo"] is True
    assert result["supply"]["rice"]["total_quantity_kg"] > 0
    assert result["supply"]["rice"]["listings_count"] == 0
    assert result["supply"]["rice"]["avg_price_per_kg"] is None


@pytest.mark.asyncio
async def test_all_regional_supply_aggregates_listings_by_region_and_crop(monkeypatch):
    listings = [
        {"location": "Chennai", "crop_name": "rice", "quantity_kg": 200, "price_per_kg": 30},
        {"location": "Chennai", "crop_name": "rice", "quantity_kg": 280, "price_per_kg": 32},
        {"location": "Kanchipuram", "crop_name": "rice", "quantity_kg": 600, "price_per_kg": 29},
        {"location": "Chengalpattu", "crop_name": "rice", "quantity_kg": 900, "price_per_kg": 31},
    ]

    class ListingCursor:
        def __aiter__(self):
            self.listings = iter(listings)
            return self

        async def __anext__(self):
            try:
                return next(self.listings)
            except StopIteration:
                raise StopAsyncIteration

    class ListingMarketCollection:
        def find(self, query):
            return ListingCursor()

    monkeypatch.setattr("services.market_service.market_collection", ListingMarketCollection())

    result = await get_all_regional_supply()
    regional_supply = result["regional_supply"]

    assert result["source"] == "farmer_listings"
    assert regional_supply["chennai"]["rice"]["total_quantity_kg"] == 480
    assert regional_supply["chennai"]["rice"]["listings_count"] == 2
    assert regional_supply["kanchipuram"]["rice"]["total_quantity_kg"] == 600
    assert regional_supply["kanchipuram"]["rice"]["listings_count"] == 1
    assert regional_supply["chengalpattu"]["rice"]["total_quantity_kg"] == 900
    assert regional_supply["chengalpattu"]["rice"]["listings_count"] == 1


@pytest.mark.asyncio
async def test_demand_analysis_recommends_sourcing_from_oversupplied_region(monkeypatch):
    async def fake_load_regional_supply_index(query=None):
        return {
            "chennai": {"groundnut": 310},
            "kanchipuram": {"groundnut": 1200},
        }

    async def no_alert_history(signals):
        return None

    def demand_estimate(**kwargs):
        expected_demand = 895 if kwargs["population_density"] > 20000 else 500
        return {
            "predicted_threshold_kg": expected_demand,
            "model": "test demand model",
            "season": "kharif",
        }

    monkeypatch.setattr("services.market_service._load_regional_supply_index", fake_load_regional_supply_index)
    monkeypatch.setattr("services.market_service._save_alert_history", no_alert_history)
    monkeypatch.setattr("services.market_service.predict_dynamic_threshold", demand_estimate)

    result = await analyze_demand("Chennai", "groundnut")
    groundnut = result["crop_analysis"]["groundnut"]

    assert groundnut["current_supply_kg"] == 310
    assert groundnut["expected_demand_kg"] == 895
    assert groundnut["market_status"] == "undersupply"
    assert groundnut["redistribution_options"][0]["region"] == "Kanchipuram"
    assert groundnut["redistribution_options"][0]["suggested_quantity_kg"] == 585


@pytest.mark.asyncio
async def test_notifications_match_dynamic_demand_analysis(monkeypatch):
    async def fake_load_regional_supply_index(query=None):
        return {"vijayawada": {"rice": 820}}

    async def no_alert_history(signals):
        return None

    monkeypatch.setattr("services.market_service._load_regional_supply_index", fake_load_regional_supply_index)
    monkeypatch.setattr("services.market_service._save_alert_history", no_alert_history)
    monkeypatch.setattr(
        "services.market_service.predict_dynamic_threshold",
        lambda **kwargs: {
            "predicted_threshold_kg": 625,
            "model": "test demand model",
            "season": "kharif",
        },
    )

    result = await get_all_market_alerts()
    rice_alert = next(
        alert for alert in result["alerts"]
        if alert["region"] == "vijayawada" and alert["crop"] == "rice"
    )

    assert rice_alert["expected_demand_kg"] == 625
    assert rice_alert["type"] == "normal"
    assert rice_alert["severity"] == "low"


@pytest.mark.asyncio
async def test_add_and_list_crop_listings_use_local_fallback_and_include_statuses(monkeypatch):
    stored_listings = []

    class OfflineMarketCollection:
        async def insert_one(self, listing):
            raise PyMongoError("database offline")

        def find(self, query):
            raise PyMongoError("database offline")

    async def insert_local(listing):
        listing_id = str(len(stored_listings) + 1)
        stored_listings.append({
            **listing,
            "_id": listing_id,
            "status": listing["status"],
            "created_at": listing["created_at"].isoformat(),
        })
        return listing_id

    async def find_local(query=None):
        if not query:
            return list(stored_listings)
        return [item for item in stored_listings if all(item.get(key) == value for key, value in query.items())]

    monkeypatch.setattr(market_service, "market_collection", OfflineMarketCollection())
    monkeypatch.setattr(market_service.local_market_store, "insert_listing", insert_local)
    monkeypatch.setattr(market_service.local_market_store, "find_listings", find_local)

    available = CropListing(
        farmer_name="Asha Farmer", location="Chennai", crop_name="Rice",
        quantity_kg=200, price_per_kg=30,
    )
    sold = CropListing(
        farmer_name="Ravi Farmer", location="Chennai", crop_name="Rice",
        quantity_kg=280, price_per_kg=32, status=CropStatus.sold,
    )

    first = await add_crop_listing(available)
    second = await add_crop_listing(sold)
    result = await market_service.get_all_listings()

    assert first["success"] and first["storage"] == "local"
    assert second["success"] and second["storage"] == "local"
    assert result["total"] == 2
    assert {listing["status"] for listing in result["listings"]} == {"available", "sold"}
    assert all(listing["location"] == "chennai" for listing in result["listings"])


def test_disease_status_reports_model_and_gemini_readiness_separately(monkeypatch):
    monkeypatch.setattr(disease_service, "TORCH_AVAILABLE", False)
    monkeypatch.setattr(disease_service, "disease_model", None)
    monkeypatch.setattr(disease_service, "MODEL_WEIGHTS_LOADED", False)
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)

    result = disease_service.get_disease_service_status()

    assert result["prediction_available"] is False
    assert "PyTorch" in result["prediction_message"]
    assert result["gemini_configured"] is False
    assert "GEMINI_API_KEY" not in result


def test_disease_status_enables_gemini_when_local_weights_are_missing(monkeypatch):
    monkeypatch.setattr(disease_service, "TORCH_AVAILABLE", True)
    monkeypatch.setattr(disease_service, "disease_model", None)
    monkeypatch.setattr(disease_service, "MODEL_WEIGHTS_LOADED", False)
    monkeypatch.setenv("GEMINI_API_KEY", "test-key")

    result = disease_service.get_disease_service_status()

    assert result["prediction_available"] is True
    assert result["prediction_source"] == "gemini"
    assert "AI-estimated" in result["prediction_message"]


def test_placeholder_gemini_key_does_not_enable_prediction(monkeypatch):
    monkeypatch.setattr(disease_service, "TORCH_AVAILABLE", True)
    monkeypatch.setattr(disease_service, "disease_model", None)
    monkeypatch.setattr(disease_service, "MODEL_WEIGHTS_LOADED", False)
    monkeypatch.setenv("GEMINI_API_KEY", "your_gemini_api_key")

    result = disease_service.get_disease_service_status()

    assert result["prediction_available"] is False
    assert result["gemini_configured"] is False


def test_gemini_classifier_accepts_only_supported_classes():
    class FakeModels:
        @staticmethod
        def generate_content(**kwargs):
            return type(
                "FakeResponse",
                (),
                {"text": '{"class_name":"Tomato___Early_blight","confidence":82}'},
            )()

    class FakeClient:
        models = FakeModels()

    prediction, confidence = disease_service.classify_image_with_gemini(
        Image.new("RGB", (8, 8)),
        FakeClient(),
    )

    assert prediction == "Tomato___Early_blight"
    assert confidence == 82.0


@pytest.mark.asyncio
async def test_predict_disease_uses_gemini_when_local_weights_are_missing(monkeypatch):
    monkeypatch.setattr(disease_service, "TORCH_AVAILABLE", False)
    monkeypatch.setattr(disease_service, "disease_model", None)
    monkeypatch.setattr(disease_service, "MODEL_WEIGHTS_LOADED", False)
    monkeypatch.setenv("GEMINI_API_KEY", "test-key")

    class FakeModels:
        @staticmethod
        def generate_content(**kwargs):
            prompt = kwargs["contents"][0]
            text = (
                '{"class_name":"Tomato___Early_blight","confidence":82}'
                if prompt.startswith("Classify the crop leaf")
                else "Gemini fallback report"
            )
            return type("FakeResponse", (), {"text": text})()

    class FakeClient:
        models = FakeModels()

    monkeypatch.setattr(
        disease_service.genai,
        "Client",
        lambda **kwargs: FakeClient(),
    )

    image_buffer = BytesIO()
    Image.new("RGB", (8, 8)).save(image_buffer, format="JPEG")
    result = await disease_service.predict_disease(image_buffer.getvalue())

    assert result["success"] is True
    assert result["raw_class"] == "Tomato___Early_blight"
    assert result["prediction_source"] == "gemini"
    assert result["confidence"] == 82.0


@pytest.mark.asyncio
async def test_predict_disease_uses_fallback_gemini_model(monkeypatch):
    monkeypatch.setattr(disease_service, "TORCH_AVAILABLE", False)
    monkeypatch.setattr(disease_service, "disease_model", None)
    monkeypatch.setattr(disease_service, "MODEL_WEIGHTS_LOADED", False)
    monkeypatch.setattr(disease_service, "GEMINI_MODEL", "primary-model")
    monkeypatch.setattr(disease_service, "GEMINI_FALLBACK_MODEL", "fallback-model")
    monkeypatch.setenv("GEMINI_API_KEY", "test-key")

    class FakeModels:
        @staticmethod
        def generate_content(*, model, contents):
            if model == "primary-model":
                raise RuntimeError("temporary overload")
            prompt = contents[0]
            text = (
                '{"class_name":"Tomato___Early_blight","confidence":82}'
                if prompt.startswith("Classify the crop leaf")
                else "Gemini fallback report"
            )
            return type("FakeResponse", (), {"text": text})()

    class FakeClient:
        models = FakeModels()

    monkeypatch.setattr(
        disease_service.genai,
        "Client",
        lambda **kwargs: FakeClient(),
    )

    image_buffer = BytesIO()
    Image.new("RGB", (8, 8)).save(image_buffer, format="JPEG")
    result = await disease_service.predict_disease(image_buffer.getvalue())

    assert result["success"] is True
    assert result["prediction_source"] == "gemini"
    assert result["prediction_model"] == "fallback-model"


@pytest.mark.asyncio
async def test_disease_route_returns_service_unavailable_when_model_is_missing(monkeypatch):
    async def unavailable_prediction(image_bytes):
        return {
            "success": False,
            "error_code": "model_unavailable",
            "error": "Trained model weights are missing.",
        }

    monkeypatch.setattr("routes.disease.predict_disease", unavailable_prediction)
    uploaded_file = UploadFile(
        filename="leaf.jpg",
        file=BytesIO(b"image-bytes"),
        headers=Headers({"content-type": "image/jpeg"}),
    )

    with pytest.raises(HTTPException) as error:
        await detect_disease(uploaded_file)

    assert error.value.status_code == 503
    assert error.value.detail == "Trained model weights are missing."
