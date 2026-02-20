import sys
sys.path.append('.')
from fastapi import APIRouter, HTTPException, Depends
from models.predict_request import SimplePredictRequest
from models.async_predict_response import AsyncPredictResponse
from services.moderations import ModerationService
from errors import ModelNotLoadedError, AdNotFoundError
import logging
from typing import Optional
from pydantic import BaseModel
from clients.kafka import KafkaProducer, kafka_producer

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Prediction"])

mod_service = ModerationService()

class CreateModerationInDto(BaseModel):
    item_id: int
    status: str
    is_violation: Optional[bool] = None
    probability: Optional[float] = None
    error_message: Optional[str] = None


async def get_kafka_producer():
    if kafka_producer is None:
        raise RuntimeError("Kafka producer is not initialized")
    return kafka_producer


@router.post("/async_predict/{item_id}", response_model=AsyncPredictResponse)
async def async_predict(request: SimplePredictRequest, 
                        producer: KafkaProducer = Depends(lambda: kafka_producer)) -> AsyncPredictResponse:

    try:
        logger.info(f"""Processing ad moderation request: item_id - {request.item_id}""")

        ready_moderation = await mod_service.get_latest_by_item_id(request.item_id)
        if ready_moderation and ready_moderation.status == "completed":
            return AsyncPredictResponse(
                task_id=ready_moderation.id,
                status=ready_moderation.status,
                message=f"Moderation was already processed, the task_id is: {ready_moderation.id}"
            )

        mod_data = CreateModerationInDto(item_id=request.item_id, status="pending")
        moderation_result = await mod_service.register(dict(mod_data))
        
        success = await producer.send_moderation_request(request.item_id, moderation_result.id)
        
        if not success:
            logger.error(f"Failed to send Kafka message for task {moderation_result.id}")

        return AsyncPredictResponse(
            task_id=moderation_result.id,
            status="pending",
            message="Moderation request accepted"
        )
        
    except AdNotFoundError:
        raise HTTPException(
            status_code=404,
            detail=f"Advertisement with ID {request.item_id} is not found"
        )
    except ModelNotLoadedError:
        raise HTTPException(
                status_code=503,
                detail="Model is not loaded. Service temporarily unavailable."
            )
    except Exception as e:
        logger.error(f'Error sending a message: {str(e)}')
        raise HTTPException(status_code=500, detail=f'Internal server error: {str(e)}')