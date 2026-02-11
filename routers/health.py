from fastapi import APIRouter, Depends
from clients.kafka import kafka_producer
from sklearn.pipeline import Pipeline

router = APIRouter(tags=["Health"])

@router.get("/health")
def health():
    return {"status": "healthy", "kafka_producer_loaded": kafka_producer._initialized}