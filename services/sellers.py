from dataclasses import dataclass
from models.seller import SellerModel
from typing import Mapping
from typing import Sequence
from typing import Any
from repositories.sellers import SellerRepository
from errors import SellerNotFoundError

@dataclass(frozen=True)
class SellerService:

    seller_repo: SellerRepository = SellerRepository()

    async def register(self, values: Mapping[str, Any]) -> SellerModel:
        return await self.seller_repo.create(**values)
    
    async def login(self, email: str, password: str) -> SellerModel:
        try:
            seller = await self.seller_repo.get_by_login_and_password(email, password)
            return seller
        except SellerNotFoundError:
            raise ValueError('Invalid login or password')

    async def delete(self, seller_id: int) -> SellerModel:
        return await self.seller_repo.delete(seller_id)
    
    async def get_many(self) -> Sequence[SellerModel]:
        return await self.seller_repo.get_many()
    
    async def get_by_seller_id(self, seller_id: int) -> SellerModel:
        return await self.seller_repo.get_by_seller_id(seller_id)
    
    async def verify(self, user_id: int) -> SellerModel:
        return await self.seller_repo.update(user_id, is_verified=True)