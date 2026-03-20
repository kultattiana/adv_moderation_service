import numpy as np
from dataclasses import dataclass
from models.ad import AdModel
from models.seller import SellerModel
from models.predict_request import PredictRequest
from typing import Mapping
from typing import Sequence
from typing import Any
from repositories.ads import AdRepository
from repositories.moderations import ModerationRepository
from repositories.sellers import SellerRepository
from errors import SellerNotFoundError

@dataclass(frozen=True)
class AdvertisementService:

    ad_repo: AdRepository = AdRepository()
    seller_repo: SellerRepository = SellerRepository()
    moderation_repo: ModerationRepository = ModerationRepository()

    async def create(self, values: Mapping[str, Any]) -> AdModel:

        seller = await self.seller_repo.get_by_seller_id(values['seller_id'])

        if not seller:
            raise SellerNotFoundError
        
        return await self.ad_repo.create(**values)
    
    async def get_for_simple_predict(self, item_id: int) -> PredictRequest:
        return await self.ad_repo.get_for_simple_predict(item_id)
    
    async def get_by_item_id(self, item_id: int) -> AdModel:
        return await self.ad_repo.get_by_item_id(item_id)
    
    async def get_by_seller_id(self, seller_id: int) -> Sequence[AdModel]:
        return await self.ad_repo.get_by_seller_id(seller_id)
    
    async def delete(self, item_id: int) -> AdModel:
        deleted_ad = await self.ad_repo.delete(item_id)
        await self.moderation_repo.delete_all_by_item_id(item_id)
        return deleted_ad

    async def get_many(self) -> Sequence[AdModel]:
        return await self.ad_repo.get_many()
    
    async def update(self, item_id: int, 
                            description: str) -> SellerModel:
        updated_ad = await self.ad_repo.update(item_id,
                                         description=description)
        await self.moderation_repo.invalidate_by_item_id(item_id)
        return updated_ad
    
    async def close(self, item_id: int) -> SellerModel:
        closed_ad = await self.ad_repo.close(item_id)
        await self.moderation_repo.delete_all_by_item_id(item_id)
        return closed_ad
        
