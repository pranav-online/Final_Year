import numpy as np
import pytest
from pydantic import ValidationError

from data.soil_data import STATE_SOIL_KEYS, get_soil_data
from routes import crop
from services import crop_service


def test_city_soil_match_takes_precedence_over_state_in_location():
    soil = get_soil_data("Hyderabad, Telangana, India")

    assert soil["N"] == 38
    assert soil["P"] == 18
    assert soil["K"] == 22


@pytest.mark.asyncio
async def test_crop_route_forwards_user_provided_field_inputs(monkeypatch):
    captured = {}

    async def fake_recommend_crop(**kwargs):
        captured.update(kwargs)
        return {"success": True}

    monkeypatch.setattr(crop, "recommend_crop", fake_recommend_crop)
    request = crop.CropInput(
        location=" Hyderabad ",
        season="Kharif",
        nitrogen=90,
        temperature=25,
        rainfall=80,
    )

    result = await crop.get_crop_recommendation(request)

    assert result["success"] is True
    assert captured == {
        "location": "Hyderabad",
        "season": "kharif",
        "nitrogen": 90,
        "phosphorous": None,
        "potassium": None,
        "ph": None,
        "temperature": 25,
        "humidity": None,
        "rainfall": 80,
    }


def test_crop_request_rejects_invalid_season_and_out_of_range_fields():
    with pytest.raises(ValidationError):
        crop.CropInput(location="Hyderabad", season="monsoon")

    with pytest.raises(ValidationError):
        crop.CropInput(location="Hyderabad", season="kharif", humidity=120)


@pytest.mark.asyncio
async def test_recommendation_uses_supplied_values_in_model_input(monkeypatch):
    captured = {}
    weather_calls = []

    class FakeModel:
        @staticmethod
        def predict_proba(input_data):
            captured["input"] = input_data[0].tolist()
            return np.array([[0.8, 0.2]])

    class FakeLabelEncoder:
        @staticmethod
        def inverse_transform(indices):
            return np.array(["rice" if index == 0 else "maize" for index in indices])

    async def fake_get_weather(_location):
        weather_calls.append(_location)
        return {
            "success": True,
            "weather": {
                "temperature": 31,
                "humidity": 68,
                "source": "demo-fallback",
            },
        }

    monkeypatch.setattr(crop_service, "crop_model", FakeModel())
    monkeypatch.setattr(crop_service, "label_encoder", FakeLabelEncoder())
    monkeypatch.setattr(crop_service, "get_weather", fake_get_weather)

    result = await crop_service.recommend_crop(
        location="Unknown farming area",
        season="kharif",
        nitrogen=90,
        ph=7.0,
        temperature=25,
        humidity=70,
        rainfall=80,
    )

    assert captured["input"] == [90, 25, 30, 25, 70, 7.0, 80]
    assert weather_calls == []
    assert result["soil_source"] == "mixed-user-provided"
    assert result["weather_source"] == "user-provided"
    assert result["rainfall_source"] == "user-provided"
    assert result["weather_inputs"] == {
        "temperature": 25,
        "humidity": 70,
        "rainfall": 80,
    }


@pytest.mark.asyncio
async def test_punjab_kharif_recommendations_exclude_out_of_region_model_winners(monkeypatch):
    async def fake_get_weather(_location):
        return {
            "success": True,
            "weather": {
                "temperature": 32,
                "humidity": 41,
                "source": "demo-fallback",
            },
        }

    monkeypatch.setattr(crop_service, "crop_model", None)
    monkeypatch.setattr(crop_service, "label_encoder", None)
    monkeypatch.setattr(crop_service, "np", None)
    monkeypatch.setattr(crop_service, "get_weather", fake_get_weather)

    result = await crop_service.recommend_crop("Punjab", "kharif")

    assert [item["crop"] for item in result["recommendations"]] == [
        "rice",
        "cotton",
        "maize",
    ]
    assert all(item["confidence"] is None for item in result["recommendations"])
    assert all(
        item["recommendation_type"] == "regional-seasonal"
        for item in result["recommendations"]
    )
    assert result["top_recommendation"] == "rice"
    assert result["recommendation_method"] == "regional-seasonal-guidance"
    assert result["regional_seasonal_guidance"]["common_crops"] == [
        "Rice (paddy)",
        "Cotton",
        "Maize",
        "Sugarcane",
        "Fodder crops",
        "Pigeon pea",
        "Green gram",
        "Black gram",
    ]
    assert result["regional_seasonal_guidance"]["not_modelled_crops"] == [
        "Sugarcane",
        "Fodder crops",
    ]


def test_all_builtin_soil_regions_have_crop_guidance_for_each_season():
    assert STATE_SOIL_KEYS <= set(crop_service.REGION_STATE_ALIASES)
    assert len(crop_service.REGION_STATE_ALIASES) == 28
    assert len(crop_service.REGIONAL_SEASONAL_CROP_PROFILES) == 28 * 3

    for state, aliases in crop_service.REGION_STATE_ALIASES.items():
        for location in aliases:
            for season in ("kharif", "rabi", "zaid"):
                profile = crop_service.get_regional_seasonal_crop_profile(
                    location, season
                )
                assert profile is not None, (state, location, season)
                assert profile["region"].lower() == state
                assert profile["priority_crops"]
                common_crop_codes = {
                    crop_service._to_model_crop_name(crop_name)
                    or crop_name.lower()
                    for crop_name in profile["common_crops"]
                }
                assert all(
                    crop_name in common_crop_codes
                    for crop_name in profile["priority_crops"]
                )


@pytest.mark.asyncio
async def test_city_alias_uses_regional_seasonal_guidance_without_model(monkeypatch):
    monkeypatch.setattr(crop_service, "crop_model", None)
    monkeypatch.setattr(crop_service, "label_encoder", None)
    monkeypatch.setattr(crop_service, "np", None)

    async def unexpected_weather_lookup(_location):
        raise AssertionError("Regional seasonal guidance should not use model weather.")

    monkeypatch.setattr(crop_service, "get_weather", unexpected_weather_lookup)

    result = await crop_service.recommend_crop("Ludhiana, Punjab", "rabi")

    assert result["success"] is True
    assert result["regional_seasonal_guidance"]["region"] == "Punjab"
    assert result["regional_seasonal_guidance"]["season"] == "rabi"
    assert [item["crop"] for item in result["recommendations"]] == [
        "chickpea",
        "lentil",
        "potato",
    ]
