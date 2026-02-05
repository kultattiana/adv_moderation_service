import numpy as np
from dataclasses import dataclass
from models.ad import AdModel
from models.seller import SellerModel
from models.predict_request import PredictRequest
from typing import Mapping
from typing import Sequence
from typing import Any
from repositories.ads import SellerRepository, AdRepository
from sklearn.pipeline import Pipeline
from model import model_singleton
from errors import SellerNotFoundError, AdNotFoundError, ModelNotLoadedError

class AdvertisementService:

    ad_repo: AdRepository = AdRepository()

    async def create(self, values: Mapping[str, Any]) -> AdModel:
        return await self.ad_repo.create(**values)
    
    async def get_for_simple_predict(self, item_id: int) -> PredictRequest:
        return await self.ad_repo.get_for_simple_predict(item_id)
    
    async def get_by_item_id(self, item_id: int) -> AdModel:
        return await self.ad_repo.get_by_item_id(item_id)
    
    async def get_by_seller_id(self, seller_id: int) -> Sequence[AdModel]:
        return await self.ad_repo.get_by_seller_id(seller_id)
    
    async def delete(self, item_id: int) -> AdModel:
        return await self.ad_repo.delete(item_id)

    async def get_many(self) -> Sequence[AdModel]:
        return await self.ad_repo.get_many()
    
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
    

    async def simple_predict(self, 
                        item_id: int):
        
        predict_request = await self.get_for_simple_predict(item_id)
        is_violation, violation_probability = await self.predict(
            predict_request.seller_id,
            predict_request.is_verified_seller, 
            predict_request.item_id,
            predict_request.name,
            predict_request.description,
            predict_request.category,
            predict_request.images_qty)
        
        return is_violation, violation_probability
    
    async def update(self, item_id: int, 
                            description: str) -> SellerModel:
        
        return await self.ad_repo.update(item_id,
                                         description=description)
        
    
        
