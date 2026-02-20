from dataclasses import dataclass
from typing import Mapping, Any, Sequence, Optional, Dict
from clients.postgres import get_pg_connection
from errors import SellerNotFoundError
from models.seller import SellerModel
from repositories.moderations import ModerationRepository
from datetime import datetime, timezone

@dataclass(frozen = True)
class SellerPostgresStorage:

    async def create(self, 
        username: str,
        email: str,
        password: str,
        is_verified: bool)-> Mapping[str, Any]:

        query = ''' INSERT INTO sellers (username, email, password, is_verified)
                    VALUES ($1, $2, $3, $4)
                    RETURNING *
                '''
        
        async with get_pg_connection() as connection:
            return dict(await connection.fetchrow(
                query, username, email, password, is_verified
            ))
    
    async def delete(self, seller_id: int) -> Mapping[str, Any]:
        query = '''
            DELETE FROM sellers
            WHERE seller_id = $1::INTEGER
            RETURNING *
        '''
        
        async with get_pg_connection() as connection:
            row = await connection.fetchrow(query, seller_id)
            
            if row:
                return dict(row)
            
            raise SellerNotFoundError()
        
    
    async def select_by_seller_id(self, seller_id: int) -> Mapping[str, Any]:
        query = '''
            SELECT *
            FROM sellers
            WHERE seller_id = $1::INTEGER
            LIMIT 1
        '''
        
        async with get_pg_connection() as connection:
            row = await connection.fetchrow(query, seller_id)
            
            if row:
                return dict(row)
            
            raise SellerNotFoundError()
    
    async def select_by_login_and_password(self, email: str, password: str) -> Mapping[str, Any]:
        query = '''
            SELECT *
            FROM sellers
            WHERE
                email = $1::TEXT
                AND password = $2::TEXT
            LIMIT 1
        '''

        async with get_pg_connection() as connection:
            row = await connection.fetchrow(query, email, password)

            if row:
                return dict(row)
            
            raise SellerNotFoundError()
    
    
    async def select_many(self) -> Sequence[Mapping[str, Any]]:
        query = '''
            SELECT *
            FROM sellers
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
            UPDATE sellers
            SET {fields_str}
            WHERE seller_id = $1::INTEGER
            RETURNING *
        '''

        async with get_pg_connection() as connection:
            row = await connection.fetchrow(query, id, *args)

            if row:
                return dict(row)
            
            raise SellerNotFoundError()
        

@dataclass(frozen=True)
class SellerRepository:
    seller_storage: SellerPostgresStorage = SellerPostgresStorage()
    moderation_repo: ModerationRepository = ModerationRepository()
    
    async def create(self, username: str,
                            email: str,
                            password: str,
                            is_verified: bool) -> SellerModel:
        
        raw_seller = await self.seller_storage.create(
                        username=username,
                        email=email,
                        password=password,
                        is_verified=is_verified
                    )
        return SellerModel(**raw_seller)
    
    async def get_by_seller_id(self, seller_id: int) -> SellerModel:
        raw_seller = await self.seller_storage.select_by_seller_id(seller_id)
        return SellerModel(**raw_seller)
    
    async def get_by_login_and_password(self, email: str, password: str) -> SellerModel:
        raw_seller = await self.seller_storage.select_by_login_and_password(email, password)
        return SellerModel(**raw_seller)  
    
    async def update(self, seller_id: int, **changes: Mapping[str, Any]) -> SellerModel:
        raw_seller = await self.seller_storage.update(seller_id, **changes)
        await self.moderation_repo.invalidate_by_seller_id(seller_id)
        return SellerModel(**raw_seller)

    async def delete(self, seller_id: int) -> SellerModel:
        raw_seller = await self.seller_storage.delete(seller_id)
        await self.moderation_repo.delete_all_by_seller_id(seller_id)
        return SellerModel(**raw_seller)
    
    async def get_many(self) -> Sequence[SellerModel]:
        return [
            SellerModel(**raw_user)
            for raw_user
            in await self.seller_storage.select_many()
        ]