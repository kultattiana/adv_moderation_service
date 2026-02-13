import asyncio
import json
import logging
from contextlib import asynccontextmanager
from typing import Dict, Any, Optional

from aiokafka import AIOKafkaConsumer, AIOKafkaProducer

from kafka_settings import KAFKA_BOOTSTRAP, TOPIC, DLQ_TOPIC, CONSUMER_GROUP
from services.moderations import ModerationService
from services.predictions import PredictionService
from errors import AdNotFoundError, ModelNotLoadedError
from datetime import datetime, timezone

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class KafkaConsumerWorker:

    MAX_RETRIES = 3
    INITIAL_RETRY_DELAY = 5
    RETRY_BACKOFF_MULTIPLIER = 2 
    
    RETRYABLE_ERRORS = (
        ConnectionError,
        TimeoutError,
        ModelNotLoadedError
    )
    
    
    def __init__(self):
        self.mod_service = ModerationService()
        self.ml_service = PredictionService()
        self.consumer: Optional[AIOKafkaConsumer] = None
        self.dlq_producer: Optional[AIOKafkaProducer] = None
    
    async def initialize(self):
        self.consumer = AIOKafkaConsumer(
            TOPIC,
            bootstrap_servers=KAFKA_BOOTSTRAP,
            group_id=CONSUMER_GROUP,
            enable_auto_commit=False,
            auto_offset_reset="earliest",
            value_deserializer=lambda x: json.loads(x.decode('utf-8')),
        )
        
        self.dlq_producer = AIOKafkaProducer(
            bootstrap_servers=KAFKA_BOOTSTRAP,
            value_serializer=lambda v: json.dumps(v).encode('utf-8'),
        )
        
        await self.consumer.start()
        await self.dlq_producer.start()
        
        logger.info(f"Started consuming {TOPIC} as group={CONSUMER_GROUP}")
    
    async def cleanup(self):
        if self.consumer:
            await self.consumer.stop()
        if self.dlq_producer:
            await self.dlq_producer.stop()
        logger.info("Worker stopped")
    
    async def send_to_dlq(self, error: str, original_message: Dict[str, Any], retry_count: int = 0):
        if not self.dlq_producer:
            return
        
        dlq_message = {
            "original": original_message,
            "error": error,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "retry_count": retry_count if retry_count is not None else self.MAX_RETRIES
        }
        
        try:
            await self.dlq_producer.send_and_wait(DLQ_TOPIC, dlq_message)
            logger.warning(f"Message sent to DLQ after {dlq_message['retry_count']} attempts: {error}")
        except Exception as e:
            logger.error(f"Failed to send to DLQ: {e}")
    
    def build_moderation_result(
        self,
        item_id: str,
        status: str,
        is_violation: bool = None,
        probability: float = None,
        error_message: Optional[str] = None,
        retry_count: int = 0
    ) -> Dict[str, Any]:
        
        result =  {
            "item_id": item_id,
            "status": status,
            "is_violation": is_violation,
            "probability": probability,
            "error_message": error_message,
            "processed_at": datetime.now(timezone.utc).replace(tzinfo=None)
        }

        return result
    
    def is_retryable_error(self, error: Exception) -> bool:
        if isinstance(error, self.RETRYABLE_ERRORS):
            return True
        
        if isinstance(error, AdNotFoundError):
            return False
        
        return False
    
    async def get_retry_count(self, message: Dict[str, Any]) -> int:
        return message.get("retry_count", 0)
    
    async def prepare_retry_message(self, original_message: Dict[str, Any], retry_count: int) -> Dict[str, Any]:
        retry_message = original_message.copy()
        retry_message["retry_count"] = retry_count + 1
        retry_message["last_retry"] = datetime.now(timezone.utc).isoformat()
        return retry_message
    
    async def schedule_retry(self, message: Dict[str, Any], retry_count: int, error: str):
        delay = self.INITIAL_RETRY_DELAY * (self.RETRY_BACKOFF_MULTIPLIER ** retry_count)
        logger.warning(f"Scheduling retry #{retry_count + 1} for message in {delay}s. Error: {error}")
        await asyncio.sleep(delay)
        asyncio.create_task(self.process_with_retry(message, retry_count + 1))
    
    async def process_with_retry(self, message: Dict[str, Any], current_retry_count: int = 0):
        try:
            await self.process_message(message, current_retry_count)
            await self.consumer.commit()
        except Exception as e:
            logger.error(f"Retry attempt {current_retry_count} failed: {e}")
            if self.is_retryable_error(e) and current_retry_count < self.MAX_RETRIES:
                await self.schedule_retry(message, current_retry_count, str(e))
            else:
                await self._handle_error(
                    item_id=message.get("item_id"),
                    task_id=message.get("task_id"),
                    error_message=str(e) if not isinstance(e, AdNotFoundError) else f"Ad {message.get('item_id')} is not found",
                    original_message=message,
                    retry_count=current_retry_count
                )
    
    async def _handle_error(
        self,
        item_id: int,
        task_id: int,
        error_message: str,
        original_message: Dict[str, Any],
        retry_count: int = 0
    ) -> bool:
        
        logger.error(f"Error processing message after {retry_count} attempts: {error_message}")
        
        query = self.build_moderation_result(
            item_id=item_id,
            status="failed",
            error_message=error_message,
        )

        try:
            await self.mod_service.update_status(task_id, query)
        except Exception as e:
            logger.error(f"Failed to update status in moderation service: {e}")
        
        await self.send_to_dlq(error_message, original_message)
        return False


    async def process_message(self, message: Dict[str, Any], retry_count: int = 0) -> bool:
        try:
            item_id = message["item_id"]
            task_id = message["task_id"]
            
            if retry_count > 0:
                logger.info(f"Retry #{retry_count} for item_id: {item_id}")
            else:
                logger.info(f"Processing event for item_id: {item_id}")
            
            is_violation, probability = await self.ml_service.simple_predict(item_id)
        
            query = self.build_moderation_result(
                item_id=item_id,
                status="completed",
                is_violation=is_violation,
                probability=probability,
            )
            
            await self.mod_service.update_status(task_id, query)
            
            logger.info(f"Successfully processed item_id: {item_id}")
            return True
            
        except AdNotFoundError as e:
            error_message = f"Ad {item_id} is not found"
            task_id = message["task_id"]
            await self._handle_error(
                item_id=item_id,
                task_id=task_id,
                error_message=error_message,
                original_message=message,
            )
            return False
            
        except Exception as e:
            if self.is_retryable_error(e):
                logger.warning(f"Retryable error for {message['item_id']}: {e}")
                raise
            else:
                logger.error(f"Non-retryable error for {message['item_id']}: {e}")
                await self._handle_error(
                    item_id=message["item_id"],
                    task_id=message["task_id"],
                    error_message=str(e),
                    original_message=message,
                    retry_count=retry_count
                )
                return False
    
    async def run(self):
        if not self.consumer:
            raise RuntimeError("Consumer not initialized")
        
        try:
            async for msg in self.consumer:
                try:
                    retry_count = await self.get_retry_count(msg.value)
                    
                    if retry_count >= self.MAX_RETRIES:
                        logger.warning(f"Message exceeded max retries ({self.MAX_RETRIES}), sending to DLQ")
                        await self._handle_error(
                            item_id=msg.value.get("item_id"),
                            task_id=msg.value.get("task_id"),
                            error_message="Exceeded maximum retry attempts",
                            original_message=msg.value,
                            retry_count=retry_count
                        )
                        await self.consumer.commit()
                        continue
                    
                    asyncio.create_task(self.process_with_retry(msg.value, retry_count))
                    await self.consumer.commit()
                        
                except Exception as e:
                    logger.error(f"Fatal error in message processing loop: {e}")
                    await asyncio.sleep(1)
                    
        except asyncio.CancelledError:
            logger.info("Worker cancelled")
        finally:
            await self.cleanup()


@asynccontextmanager
async def worker_lifespan():
    worker = KafkaConsumerWorker()
    await worker.initialize()
    try:
        yield worker
    finally:
        await worker.cleanup()


async def main():
    async with worker_lifespan() as worker:
        await worker.run()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Worker stopped by user")
    except Exception as e:
        logger.error(f"Worker crashed: {e}")
        raise