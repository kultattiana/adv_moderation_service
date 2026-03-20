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
from observability.metrics import PREDICTION_ERRORS_TOTAL
from routers.health import sentry_sdk
from dependencies import ModServiceDepend
from typing import Annotated
from auth_middleware.auth import auth
from models.seller import SellerModel
from aiokafka.errors import KafkaError

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Prediction"])

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
                        mod_service: ModServiceDepend,
                        _: Annotated[SellerModel, Depends(auth)],
                        producer: KafkaProducer = Depends(lambda: kafka_producer)) -> AsyncPredictResponse:

    with sentry_sdk.configure_scope() as scope:
        scope.set_tag("endpoint", "async_predict")
        scope.set_tag("http_method", "POST")
        scope.set_context("request_data", {
            "item_id": request.item_id
        })

    try:
        logger.info(f"""Processing ad moderation request: item_id - {request.item_id}""")

        ready_moderation = await mod_service.get_latest_by_item_id(request.item_id)

        if ready_moderation and ready_moderation.status == "completed":
            return AsyncPredictResponse(
                task_id=ready_moderation.id,
                status=ready_moderation.status,
                message=f"Moderation was already processed, the task_id is: {ready_moderation.id}"
            )
        if ready_moderation and ready_moderation.status == "pending":
            return AsyncPredictResponse(
                task_id=ready_moderation.id,
                status=ready_moderation.status,
                message=f"Moderation is already in progress, the task_id is: {ready_moderation.id}"
            )
        
        if ready_moderation and ready_moderation.status == "failed":
            return AsyncPredictResponse(
                task_id=ready_moderation.id,
                status=ready_moderation.status,
                message=f"Moderation was already processed and failed: {ready_moderation.error_message}."
            )
        
        mod_data = CreateModerationInDto(item_id=request.item_id, status="pending")
        moderation_result = await mod_service.register(dict(mod_data))
        
        await producer.send_moderation_request(request.item_id, moderation_result.id)

        return AsyncPredictResponse(
            task_id=moderation_result.id,
            status="pending",
            message="Moderation request accepted"
        )
        
    except AdNotFoundError as e:

        sentry_sdk.capture_exception(e)
        sentry_sdk.set_tag("error_type", "ad_not_found")
        sentry_sdk.set_context("error_details", {
            "item_id": request.item_id
        })

        PREDICTION_ERRORS_TOTAL.labels(error_type = "ad_error").inc()
        raise HTTPException(
            status_code=404,
            detail=f"Advertisement with ID {request.item_id} is not found"
        )
    except ModelNotLoadedError:

        with sentry_sdk.configure_scope() as scope:
            scope.set_tag("error_type", "model_not_loaded")
            scope.set_context("error_details", {
                "item_id": request.item_id
            })

        PREDICTION_ERRORS_TOTAL.labels(error_type = "model_unavailable").inc()
        raise HTTPException(
                status_code=503,
                detail="Model is not loaded. Service temporarily unavailable."
            )
    
    except KafkaError:
        with sentry_sdk.configure_scope() as scope:
                scope.set_tag("error_type", "kafka_send_failed")
                scope.set_context("error_details", {
                    "item_id": request.item_id,
                    "task_id": moderation_result.id
                })
            
        sentry_sdk.capture_message(
            f"Kafka message send failed for task {moderation_result.id}",
            level="warning",
            extras={
                "item_id": request.item_id,
                "task_id": moderation_result.id
            }
        )

        PREDICTION_ERRORS_TOTAL.labels(error_type = "prediction_error").inc()
        logger.error(f'Error sending a message: {str(e)}')
        raise HTTPException(status_code=500, detail=f"Failed to send Kafka message for task {moderation_result.id}")

    except Exception as e:

        with sentry_sdk.configure_scope() as scope:
            scope.set_tag("error_type", "prediction_error")
            scope.set_context("error_details", {
                "item_id": request.item_id,
                "error": str(e),
                "error_type": type(e).__name__
            })

        PREDICTION_ERRORS_TOTAL.labels(error_type = "prediction_error").inc()
        logger.error(f'Error sending a message: {str(e)}')
        raise HTTPException(status_code=500, detail=f'Internal server error: {str(e)}')