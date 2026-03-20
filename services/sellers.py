from dataclasses import dataclass
from models.seller import SellerModel
from typing import Mapping
from typing import Sequence
from typing import Any
from repositories.sellers import SellerRepository
from repositories.moderations import ModerationRepository
from repositories.accounts import AccountRepository
from errors import SellerNotFoundError

@dataclass(frozen=True)
class SellerService:

    seller_repo: SellerRepository = SellerRepository()
    moderation_repo: ModerationRepository = ModerationRepository()
    account_repo: AccountRepository = AccountRepository()
    

    async def register(self, values: Mapping[str, Any]) -> SellerModel:

        created_seller = await self.seller_repo.create(**values)
        raw_account = await self.account_repo.create(
                        login=values["username"],
                        password=values["password"],
                        seller_id=created_seller.seller_id,
                        is_blocked=False
                    )
        
        return created_seller
    
    async def login(self, email: str, password: str) -> SellerModel:
        try:
            seller = await self.seller_repo.get_by_login_and_password(email, password)
            return seller
        except SellerNotFoundError:
            raise ValueError('Invalid login or password')

    async def delete(self, seller_id: int) -> SellerModel:
        deleted_seller = await self.seller_repo.delete(seller_id)
        await self.moderation_repo.delete_all_by_seller_id(seller_id)
        await self.account_repo.delete_all_by_seller_id(seller_id)
        return deleted_seller
    
    async def get_many(self) -> Sequence[SellerModel]:
        return await self.seller_repo.get_many()
    
    async def get_by_seller_id(self, seller_id: int) -> SellerModel:
        return await self.seller_repo.get_by_seller_id(seller_id)
    
    async def verify(self, seller_id: int) -> SellerModel:
        updated_seller = await self.seller_repo.update(seller_id, is_verified=True)
        await self.moderation_repo.invalidate_by_seller_id(seller_id)
        await self.account_repo.invalidate_by_seller_id(seller_id)
        return updated_seller