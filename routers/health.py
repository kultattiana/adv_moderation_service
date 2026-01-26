from fastapi import APIRouter, Depends
from routers.predict import get_model
from sklearn.pipeline import Pipeline

router = APIRouter(tags=["Health"])

@router.get("/health")
def health(model: Pipeline = Depends(get_model)):
    return {"status": "healthy", "model_loaded": model is not None}