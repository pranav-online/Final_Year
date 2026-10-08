from fastapi import APIRouter, UploadFile, File, HTTPException, status
from services.disease_service import get_disease_service_status, predict_disease

router = APIRouter(prefix="/disease", tags=["Disease Detection"])
MAX_IMAGE_SIZE_BYTES = 10 * 1024 * 1024


@router.get("/status")
async def disease_status():
    return get_disease_service_status()

@router.post("/predict")
async def detect_disease(file: UploadFile = File(...)):
    # Validate file type
    if not file.content_type or not file.content_type.startswith("image/"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only image files are allowed"
        )

    # Read image bytes
    image_bytes = await file.read(MAX_IMAGE_SIZE_BYTES + 1)
    if len(image_bytes) > MAX_IMAGE_SIZE_BYTES:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail="Image must be 10 MB or smaller"
        )
    if not image_bytes:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="The uploaded image is empty"
        )

    # Run prediction
    result = await predict_disease(image_bytes)

    if not result["success"]:
        if result.get("error_code") == "model_unavailable":
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=result["error"]
            )
        if result.get("error_code") == "invalid_image":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=result["error"]
            )
        if result.get("error_code") == "classification_failed":
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail=result["error"]
            )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Prediction failed due to an internal error"
        )

    return result