from fastapi import APIRouter, Depends
from clients.kafka import kafka_producer

router = APIRouter(tags=["Health"])

@router.get("/health")
def health():
    return {"status": "healthy", "kafka_producer_loaded": kafka_producer._initialized}