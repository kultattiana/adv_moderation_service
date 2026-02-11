import json
import logging
from datetime import datetime, timezone
from typing import Optional, Dict, Any
from aiokafka import AIOKafkaProducer
from aiokafka.errors import KafkaError
from kafka_settings import TOPIC

logger = logging.getLogger(__name__)

from kafka_settings import KAFKA_BOOTSTRAP

class KafkaProducer:

    _instance: Optional['KafkaProducer'] = None
    _initialized: bool = False
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(KafkaProducer, cls).__new__(cls)
        return cls._instance
    
    def __init__(self):
        if KafkaProducer._initialized:
            return
        
        self._bootstrap: Optional[str] = None
        self._producer: Optional[AIOKafkaProducer] = None
        KafkaProducer._initialized = True
        
    async def configure(self, bootstrap_servers: str) -> None:
        self._bootstrap = bootstrap_servers
        
    async def start(self) -> None:
        try:
            self._producer = AIOKafkaProducer(bootstrap_servers=self._bootstrap,
                                                value_serializer=lambda v: json.dumps(v).encode('utf-8'),
                                                key_serializer=lambda k: str(k).encode('utf-8'))
            await self._producer.start()
            logger.info(
                f"Kafka Moderation Producer Up"
                f"Servers: {self._bootstrap}"
            )
        except Exception as e:
            logger.error(f"Kafka Producer launch error: {e}")
            raise
    
    async def stop(self) -> None:
        if self._producer:
            try:
                await self._producer.stop()
                logger.info("Kafka Producer stopped")
            except Exception as e:
                logger.error(f"Kafka Producer launch error: {e}")
            finally:
                self._producer = None
    
    
    async def send_moderation_request(self, item_id: int, task_id: int) -> bool:
        message = {
            "task_id": task_id,
            "item_id": item_id,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "event_type": "moderation_request",
            "metadata": {
                "source": "advertisement_service",
                "version": "1.0"
            }
        }
        
        try:
            await self._producer.send_and_wait(
                topic=TOPIC,
                key=str(item_id),
                value=message
            )
            
            logger.info(
                f"Moderation request sent to Kafka. Item ID: {item_id}"
            )
            return True
            
        except KafkaError as e:
            logger.error(f"Error in Kafka during sending moderation request for item_id={item_id}: {e}")
            return False
            
        except Exception as e:
            logger.error(f"Unexpected error during sending the moderation request: {e}")
            return False
    
    
    @property
    def is_ready(self) -> bool:
        return self._producer is not None
    
    async def flush(self):
        if self._producer:
            try:
                await self._producer.flush()
                logger.debug("Kafka Producer Buffer cleaned")
            except Exception as e:
                logger.error(f"Error during : {e}")

kafka_producer = KafkaProducer()