import numpy as np
from dataclasses import dataclass
from models.predict_request import PredictRequest
from typing import Any
from repositories.ads import  AdRepository
from sklearn.pipeline import Pipeline
from model import model_singleton
from errors import ModelNotLoadedError
from typing import Dict, Any, Optional
from datetime import datetime, timezone
from services.moderations import ModerationService
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class PredictionService:

    ad_repo: AdRepository = AdRepository()
    mod_service = ModerationService()
    
    async def get_for_simple_predict(self, item_id: int) -> PredictRequest:
        return await self.ad_repo.get_for_simple_predict(item_id)
    
    def get_model() -> Pipeline:
        return model_singleton._model
    
    async def predict(self, 
                        seller_id: int,
                        is_verified_seller: bool, 
                        item_id: int,
                        name: str,
                        description: str,
                        category: int,
                        images_qty: int):
        
        if not model_singleton.is_loaded:
            raise ModelNotLoadedError
        
        model = model_singleton._model
        verified_feature = 1.0 if is_verified_seller else 0.0
        images_normalized = min(images_qty, 10) / 10.0
        desc_length_normalized = len(description) / 1000.0
        category_normalized = category / 100.0
        
        features_array = np.array([[
            verified_feature,
            images_normalized,
            desc_length_normalized,
            category_normalized
        ]])
        
        prediction_class = model.predict(features_array)[0]
        probabilities = model.predict_proba(features_array)[0]
        violation_probability = float(probabilities[1])
        is_violation = bool(prediction_class)

        return is_violation, violation_probability
    
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

    async def simple_predict(self, 
                        item_id: int, task_id: int):
        
        predict_request = await self.get_for_simple_predict(item_id)
        is_violation, violation_probability = await self.predict(
            predict_request.seller_id,
            predict_request.is_verified_seller, 
            predict_request.item_id,
            predict_request.name,
            predict_request.description,
            predict_request.category,
            predict_request.images_qty)
        
        query = self.build_moderation_result(
                item_id=item_id,
                status="completed",
                is_violation=is_violation,
                probability=violation_probability,
            )

        logger.info(f"Updating status: {task_id}")
        await self.mod_service.update_status(task_id, query)
        
        return is_violation, violation_probability
    