from dataclasses import dataclass
from typing import Mapping, Any, Sequence, Optional, Dict
from clients.postgres import get_pg_connection
from errors import ModerationNotFoundError
from models.moderation import ModerationModel

@dataclass(frozen = True)
class ModerationPostgresStorage:

    async def create(self, 
        item_id: int,
        status: str,
        is_violation: bool,
        probability: float,
        error_message: str)-> Mapping[str, Any]:

        query = ''' INSERT INTO moderation_results (item_id, status, is_violation, probability, error_message)
                    VALUES ($1, $2, $3, $4, $5)
                    RETURNING *
                '''
        
        async with get_pg_connection() as connection:
            return dict(await connection.fetchrow(
                query, item_id, status, is_violation, probability, error_message
            ))
    
    async def ensure_idempotency(self, item_id: int,
                                    status: str,
                                    is_violation: bool,
                                    probability: float,
                                    error_message: str) -> bool:
        query = ''' INSERT INTO moderation_results (item_id, status, is_violation, probability, error_message)
                    VALUES ($1, $2, $3, $4, $5)
                    RETURNING *
                '''
        async with get_pg_connection() as connection:
            result = await connection.execute(
               query, item_id, status, is_violation, probability, error_message
            )
        return not result.endswith("0")

    
    async def select_by_task_id(self, id: int) -> Mapping[str, Any]:
        query = '''
            SELECT *
            FROM moderation_results
            WHERE id = $1::INTEGER
            LIMIT 1
        '''
        
        async with get_pg_connection() as connection:
            row = await connection.fetchrow(query, id)
            
            if row:
                return dict(row)
            
            raise ModerationNotFoundError()
    
    
    
    async def select_many(self) -> Sequence[Mapping[str, Any]]:
        query = '''
            SELECT *
            FROM moderation_results
            ORDER BY created_at DESC
        '''
        
        async with get_pg_connection() as connection:
            rows = await connection.fetch(query)
            return [dict(row) for row in rows]
    
    async def delete(self, seller_id: int) -> Mapping[str, Any]:
        query = '''
            DELETE FROM moderation_results
            WHERE id = $1::INTEGER
            RETURNING *
        '''
        
        async with get_pg_connection() as connection:
            row = await connection.fetchrow(query, seller_id)
            
            if row:
                return dict(row)
            
            raise ModerationNotFoundError()
    
    async def update(self, id: int, **updates: Any) -> Mapping[str, Any]:
        keys, args = [], []

        for key, value in updates.items():
            keys.append(key)
            args.append(value)

        fields_str = ', '.join([f'{key} = ${i + 2}' for i, key in enumerate(keys)])

        query = f'''
            UPDATE moderation_results
            SET {fields_str}
            WHERE id = $1::INTEGER
            RETURNING *
        '''

        async with get_pg_connection() as connection:
            row = await connection.fetchrow(query, id, *args)

            if row:
                return dict(row)
            
            raise ModerationNotFoundError()
        
        

@dataclass(frozen=True)
class ModerationRepository:
    moderation_storage: ModerationPostgresStorage = ModerationPostgresStorage()
    
    async def create(self, item_id: int,
                            status: str,
                            is_violation: bool,
                            probability: float,
                            error_message: str) -> ModerationModel:
        
        raw_mod = await self.moderation_storage.create(
                        item_id = item_id,
                        status = status,
                        is_violation = is_violation,
                        probability = probability,
                        error_message = error_message
                    )
        return ModerationModel(**raw_mod)
    
    async def ensure_idempotency(self, item_id: int,
                            status: str,
                            is_violation: bool,
                            probability: float,
                            error_message: str) -> bool:
        
        is_idempotent = await self.moderation_storage.ensure_idempotency(
                        item_id = item_id,
                        status = status,
                        is_violation = is_violation,
                        probability = probability,
                        error_message = error_message
                    )
        return is_idempotent
    
    async def get_by_task_id(self, id: int) -> ModerationModel:
        raw_mod = await self.moderation_storage.select_by_task_id(id)
        return ModerationModel(**raw_mod)
    
    async def update(self, id: int, **changes: Mapping[str, Any]) -> ModerationModel:
        raw_mod = await self.moderation_storage.update(id, **changes)
        return ModerationModel(**raw_mod)

    async def delete(self, task_id: int) -> ModerationModel:
        raw_mod = await self.moderation_storage.delete(task_id)
        return ModerationModel(**raw_mod)
    
    async def get_many(self) -> Sequence[ModerationModel]:
        return [
            ModerationModel(**raw_mod)
            for raw_mod
            in await self.moderation_storage.select_many()
        ]
    