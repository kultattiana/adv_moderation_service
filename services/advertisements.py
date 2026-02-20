import numpy as np
from dataclasses import dataclass
from models.ad import AdModel
from models.seller import SellerModel
from models.predict_request import PredictRequest
from typing import Mapping
from typing import Sequence
from typing import Any
from repositories.ads import AdRepository

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
    
    async def update(self, item_id: int, 
                            description: str) -> SellerModel:
        return await self.ad_repo.update(item_id,
                                         description=description)
    
    async def close(self, item_id: int) -> SellerModel:
        return await self.ad_repo.close(item_id)
        
