from fastapi import APIRouter, Depends
from model import model_singleton
from sklearn.pipeline import Pipeline

router = APIRouter(tags=["Health"])

@router.get("/health")
def health():
    return {"status": "healthy", "model_loaded": model_singleton.is_loaded}