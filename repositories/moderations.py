from dataclasses import dataclass
from typing import Mapping, Any, Sequence, Optional, Dict
from clients.postgres import get_pg_connection
from errors import ModerationNotFoundError
from models.moderation import ModerationModel
from clients.redis import get_redis_connection
from json import loads, dumps
from datetime import timedelta
from async_lru import alru_cache
import logging
from datetime import datetime, date
import json

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)

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
    
    async def select_latest_by_item_id(self, id: int) -> Mapping[str, Any]:
        query = '''
            SELECT *
            FROM moderation_results
            WHERE item_id = $1::INTEGER
            ORDER BY processed_at DESC
            LIMIT 1
        '''
        
        async with get_pg_connection() as connection:
            row = await connection.fetchrow(query, id)
            
            if row:
                return dict(row)
            
            return None
        
    
    async def select_many(self) -> Sequence[Mapping[str, Any]]:
        query = '''
            SELECT *
            FROM moderation_results
            ORDER BY created_at DESC
        '''
        
        async with get_pg_connection() as connection:
            rows = await connection.fetch(query)
            return [dict(row) for row in rows]
    
    async def delete(self, id: int) -> Mapping[str, Any]:
        query = '''
            DELETE FROM moderation_results
            WHERE id = $1::INTEGER
            RETURNING *
        '''
        
        async with get_pg_connection() as connection:
            row = await connection.fetchrow(query, id)
            
            if row:
                return dict(row)
            
            raise ModerationNotFoundError()
    
    async def delete_by_item_id(self, item_id: int) -> None:
        query = "DELETE FROM moderation_results WHERE item_id = $1"
        async with get_pg_connection() as conn:
            await conn.execute(query, item_id)
    
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
        
    async def select_item_ids_by_seller_id(self, seller_id: int) -> Sequence[int]:
        query = """
            SELECT item_id 
            FROM ads 
            WHERE seller_id = $1 AND is_closed = false
        """
        async with get_pg_connection() as connection:
            rows = await connection.fetch(query, seller_id)
            return [row['item_id'] for row in rows]

class CustomJSONEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, (datetime, date)):
            return obj.isoformat()
        return super().default(obj)
        
@dataclass(frozen=True)
class ModerationRedisStorage:

    # TTL выбран равным 14 дням исходя из следующих соображений:
    # 1. Результаты модерации объявлений редко меняются: после проверки объявление
    #    остаётся в том же статусе, если только владелец не отредактирует его, 
    #    или статус продавца не поменяется,
    #    редактирование происходит нечасто, поэтому данные можно кэшировать надолго
    # 2. Увеличение TTL до 14 дней значительно снижает нагрузку на БД для повторных
    #    запросов одного и того же объявления

    _TTL: timedelta = timedelta(days=14)
    
    TASK_PREFIX = "task:"
    ITEM_PREFIX = "item:"

    async def set_by_task_id(self, task_id: int, row: Mapping[str, Any]) -> None:
        async with get_redis_connection() as connection:
            pipeline = connection.pipeline()
            pipeline.set(
                name=f"{self.TASK_PREFIX}{task_id}",
                value=dumps(row, cls=CustomJSONEncoder),
            )
            pipeline.expire(f"{self.TASK_PREFIX}{task_id}", self._TTL)
            await pipeline.execute()
    
    async def set_latest_by_item_id(self, item_id: int, row: Mapping[str, Any]) -> None:
        async with get_redis_connection() as connection:
            pipeline = connection.pipeline()
            pipeline.set(
                name=f"{self.ITEM_PREFIX}{item_id}",
                value=dumps(row, cls=CustomJSONEncoder),
            )
            pipeline.expire(f"{self.ITEM_PREFIX}{item_id}", self._TTL)
            await pipeline.execute()
    
    async def get_by_task_id(self, task_id: int) -> Mapping[str, Any] | None:
        async with get_redis_connection() as connection:
            row = await connection.get(f"{self.TASK_PREFIX}{task_id}")

            if row:
                return loads(row)
            
            return None
    
    async def get_latest_by_item_id(self, item_id: int) -> Mapping[str, Any] | None:
        async with get_redis_connection() as connection:
            row = await connection.get(f"{self.ITEM_PREFIX}{item_id}")

            if row:
                return loads(row)
            
            return None

    async def delete_by_task_id(self, task_id: int) -> None:
        async with get_redis_connection() as connection:
            await connection.delete(f"{self.TASK_PREFIX}{task_id}")
    
    async def delete_latest_by_item_id(self, item_id: int) -> None:
        async with get_redis_connection() as connection:
            await connection.delete(f"{self.ITEM_PREFIX}{item_id}")

@dataclass(frozen=True)
class ModerationRepository:
    moderation_storage: ModerationPostgresStorage = ModerationPostgresStorage()
    moderation_redis_storage: ModerationRedisStorage = ModerationRedisStorage()
    
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
        
        mod_model = ModerationModel(**raw_mod)
        
        return mod_model
    
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
        raw_mod = await self.moderation_redis_storage.get_by_task_id(id)

        if raw_mod:
            return ModerationModel(**raw_mod)
        
        raw_mod = await self.moderation_storage.select_by_task_id(id)

        if raw_mod and raw_mod["status"] == "completed":
            await self.moderation_redis_storage.set_by_task_id(id, raw_mod)
            await self.moderation_redis_storage.set_latest_by_item_id(raw_mod['item_id'], raw_mod)

        return ModerationModel(**raw_mod)

    async def get_latest_by_item_id(self, item_id: int) -> Optional[ModerationModel]:

        raw_mod = await self.moderation_redis_storage.get_latest_by_item_id(item_id)

        if raw_mod:
            return ModerationModel(**raw_mod)

        raw_mod = await self.moderation_storage.select_latest_by_item_id(item_id)
        
        if raw_mod and raw_mod["status"] == "completed":
            await self.moderation_redis_storage.set_latest_by_item_id(item_id, raw_mod)
            await self.moderation_redis_storage.set_by_task_id(raw_mod['id'], raw_mod)
            return ModerationModel(**raw_mod)
        
        return None
    

    async def update(self, id: int, **changes: Mapping[str, Any]) -> ModerationModel:
        raw_mod = await self.moderation_storage.update(id, **changes)
        
        mod_model = ModerationModel(**raw_mod)

        if mod_model.status == "completed":
            await self.moderation_redis_storage.set_by_task_id(mod_model.id, raw_mod)
            await self.moderation_redis_storage.set_latest_by_item_id(mod_model.item_id, raw_mod)
        
        return mod_model

    async def delete(self, task_id: int) -> ModerationModel:
        moderation = await self.get_by_task_id(task_id)
        
        raw_mod = await self.moderation_storage.delete(task_id)
        await self.moderation_redis_storage.delete_by_task_id(task_id)
        
        latest = await self.get_latest_by_item_id(moderation.item_id)
        if latest and latest.id == task_id:
            await self.moderation_redis_storage.delete_latest_by_item_id(moderation.item_id)
            next_latest = await self.moderation_storage.select_latest_by_item_id(moderation.item_id)
            if next_latest and next_latest.status == "completed":
                await self.moderation_redis_storage.set_latest_by_item_id(moderation.item_id, next_latest)
                await self.moderation_redis_storage.set_by_task_id(next_latest['id'], next_latest)
                
        return ModerationModel(**raw_mod)
    
    async def delete_all_by_item_id(self, item_id: int) -> None:

        latest = await self.get_latest_by_item_id(item_id)
        await self.moderation_storage.delete_by_item_id(item_id)
        if latest:
            await self.moderation_redis_storage.delete_by_task_id(latest.id)
        await self.moderation_redis_storage.delete_latest_by_item_id(item_id)
        
        logger.info(f"All moderation results for item_id={item_id} deleted")
    
    async def delete_all_by_seller_id(self, seller_id: int) -> None:

        item_ids = await self.moderation_storage.select_item_ids_by_seller_id(seller_id)
        
        if not item_ids:
            logger.info(f"No items found for seller_id={seller_id}")
            return
        
        for item_id in item_ids:
            await self.delete_all_by_item_id(item_id)
        
        logger.info(f"Deleted cache and moderation results for seller_id={seller_id}, {len(item_ids)} items affected")

    
    async def invalidate_by_item_id(self, item_id: int) -> None:
        latest = await self.get_latest_by_item_id(item_id)
        
        if latest:
            await self.moderation_redis_storage.delete_by_task_id(latest.id)
            await self.moderation_redis_storage.delete_latest_by_item_id(item_id)
            await self.moderation_storage.delete_by_item_id(item_id)
            logger.info(f"Cache invalidated for item_id={item_id}, task_id={latest.id}")
    
    async def invalidate_by_seller_id(self, seller_id: int) -> None:
        
        item_ids = await self.moderation_storage.select_item_ids_by_seller_id(seller_id)
        
        if not item_ids:
            logger.info(f"No items found for seller_id={seller_id}")
            return
        
        for item_id in item_ids:
            await self.invalidate_by_item_id(item_id)
        
        logger.info(f"Invalidated cache for seller_id={seller_id}, {len(item_ids)} items affected")

        
    async def get_many(self) -> Sequence[ModerationModel]:
        return [
            ModerationModel(**raw_mod)
            for raw_mod
            in await self.moderation_storage.select_many()
        ]
    