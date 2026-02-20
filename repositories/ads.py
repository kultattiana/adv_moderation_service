from dataclasses import dataclass
from typing import Mapping, Any, Sequence, Optional, Dict
from clients.postgres import get_pg_connection
from errors import AdNotFoundError, SellerNotFoundError
from models.seller import SellerModel
from models.ad import AdModel
from models.predict_request import PredictRequest
from repositories.sellers import SellerPostgresStorage
from repositories.moderations import ModerationRepository
from datetime import datetime, timezone

@dataclass(frozen=True)
class AdPostgresStorage:

    async def create(self, seller_id: int,
                            name: str,
                            description: str,
                            category: int,
                            images_qty: int
                        ) -> Mapping[str, any]:
        query = '''
            INSERT INTO ads (seller_id, name, description, category, images_qty)
            VALUES ($1, $2, $3, $4, $5)
            RETURNING *
        '''

        async with get_pg_connection() as connection:
            return dict(await connection.fetchrow(query, seller_id, name, 
                                                  description, category, images_qty))
    
    async def select_by_item_id(self, item_id: int) -> Mapping[str, any]:

        query = '''
            SELECT *
            FROM ads
            WHERE item_id = $1::INTEGER
            LIMIT 1
        '''

        async with get_pg_connection() as connection:
            row = await connection.fetchrow(query, item_id)

            if row:
                return dict(row)
            raise AdNotFoundError()
    
    async def select_for_prediction(self, item_id: int) -> Mapping[str, Any]:
        query = '''
            SELECT 
                s.seller_id as seller_id,
                s.is_verified as is_verified_seller,
                a.item_id as item_id,
                a.name,
                COALESCE(a.description, '') as description,
                a.category,
                a.images_qty
            FROM ads a
            JOIN sellers s 
            ON a.seller_id = s.seller_id
                AND a.is_closed = FALSE
            WHERE a.item_id = $1::INTEGER
            LIMIT 1
        '''
        
        async with get_pg_connection() as connection:
            row = await connection.fetchrow(query, item_id)
            
            if row:
                return dict(row)
            
            raise AdNotFoundError()
    
    async def delete(self, item_id: int) -> Mapping[str, any]:
        query = '''
            DELETE FROM ads
            WHERE item_id = $1::INTEGER
            RETURNING *
        '''
        
        async with get_pg_connection() as connection:
            row = await connection.fetchrow(query, item_id)
            
            if row:
                return dict(row)
            
            raise AdNotFoundError()
    
    
    async def select_by_seller_id(self, seller_id: int) -> Sequence[Mapping[str, any]]:
        query = '''
            SELECT *
            FROM ads
            WHERE seller_id = $1::INTEGER
            ORDER BY created_at DESC
        '''
        
        async with get_pg_connection() as connection:
            rows = await connection.fetch(query, seller_id)

            if rows:
                return [dict(row) for row in rows]
            raise SellerNotFoundError
    
    async def select_many(self) -> Sequence[Mapping[str, Any]]:
        query = '''
            SELECT *
            FROM ads
            ORDER BY created_at DESC
        '''
        
        async with get_pg_connection() as connection:
            rows = await connection.fetch(query)
            return [dict(row) for row in rows]
    
    async def update(self, id: int, **updates: Any) -> Mapping[str, Any]:
        keys, args = [], []

        for key, value in updates.items():
            keys.append(key)
            args.append(value)
        
        keys.append('updated_at')
        args.append(datetime.now(timezone.utc).replace(tzinfo=None))

        fields_str = ', '.join([f'{key} = ${i + 2}' for i, key in enumerate(keys)])
        query = f'''
            UPDATE ads
            SET {fields_str}
            WHERE item_id = $1::INTEGER
            RETURNING *
        '''

        async with get_pg_connection() as connection:
            row = await connection.fetchrow(query, id, *args)

            if row:
                return dict(row)
            
            raise AdNotFoundError()
        
        
@dataclass(frozen=True)
class AdRepository:
    ad_storage: AdPostgresStorage = AdPostgresStorage()
    seller_storage: SellerPostgresStorage = SellerPostgresStorage()
    moderation_repo: ModerationRepository = ModerationRepository()
    
    async def create(self, seller_id: int,
                            name: str,
                            description: str,
                            category: int,
                            images_qty: int) -> AdModel:
        
        seller = await self.seller_storage.select_by_seller_id(seller_id)

        if not seller:
            raise SellerNotFoundError
        
        raw_ad = await self.ad_storage.create(
            seller_id=seller_id,
            name=name,
            description=description,
            category=category,
            images_qty=images_qty
        )

        return AdModel(**raw_ad)
    
    async def get_for_simple_predict(self, item_id: int) -> PredictRequest:
        item_data = await self.ad_storage.select_for_prediction(item_id)
        return PredictRequest(**item_data)
    
    async def get_by_item_id(self, item_id: int) -> AdModel:
        raw_ad = await self.ad_storage.select_by_item_id(item_id)
        return AdModel(**raw_ad)
    
    async def get_by_seller_id(self, seller_id: int) -> Sequence[AdModel]:
        raw_ads = await self.ad_storage.select_by_seller_id(seller_id)
        return [AdModel(**ad) for ad in raw_ads]
    
    async def delete(self, item_id: int) -> AdModel:
        raw_ad = await self.ad_storage.delete(item_id)
        await self.moderation_repo.delete_all_by_item_id(item_id)
        return AdModel(**raw_ad)
    

    async def get_many(self) -> Sequence[AdModel]:
        return [
            AdModel(**raw_ad)
            for raw_ad
            in await self.ad_storage.select_many()
        ]

    async def update(self, item_id: int, **changes: Mapping[str, Any]) -> SellerModel:
        raw_ad= await self.ad_storage.update(item_id, **changes)
        await self.moderation_repo.invalidate_by_item_id(item_id)
        return AdModel(**raw_ad)
    
    async def close(self, item_id: int) -> None:
        raw_ad = await self.ad_storage.update(item_id, is_closed=True)
        await self.moderation_repo.delete_all_by_item_id(item_id)
        return AdModel(**raw_ad)
