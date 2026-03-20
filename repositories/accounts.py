from dataclasses import dataclass
from typing import Mapping, Any, Sequence, Optional, Dict
from clients.postgres import get_pg_connection
from errors import SellerNotFoundError, UnauthorizedError
from models.account import AccountModel
from repositories.moderations import ModerationRepository
from datetime import datetime, timezone
from utils.hash import generate_salt, verify_password, hash_password
import time
from observability.metrics import DB_QUERY_DURATION
from clients.redis import get_redis_connection
from json import loads, dumps
from datetime import timedelta
from datetime import datetime, date
import json
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)

@dataclass(frozen = True)
class AccountPostgresStorage:

    async def create(self, 
        login: str,
        password: str,
        salt: str, 
        seller_id: int,
        is_blocked: bool)-> Mapping[str, Any]:

        query = ''' INSERT INTO accounts (login, password, salt, seller_id, is_blocked)
                    VALUES ($1, $2, $3, $4, $5)
                    RETURNING *
                '''
        
        async with get_pg_connection(operation="insert") as connection:

            start = time.perf_counter()
            row = await connection.fetchrow(
                    query, login, password, salt, seller_id, is_blocked
                )
            duration = time.perf_counter() - start
            DB_QUERY_DURATION.labels(operation="insert").observe(duration)

            return dict(row)
    

    async def delete(self, id: int) -> Mapping[str, Any]:
        query = '''
            DELETE FROM accounts
            WHERE id = $1::INTEGER
            RETURNING *
        '''
        
        async with get_pg_connection(operation="delete") as connection:

            start = time.perf_counter()
            row = await connection.fetchrow(query, id)
            duration = time.perf_counter() - start

            DB_QUERY_DURATION.labels(operation="delete").observe(duration)

            if row:
                return dict(row)
            
            raise UnauthorizedError()
        
    
    async def select_by_id(self, id: int) -> Mapping[str, Any]:
        query = '''
            SELECT *
            FROM accounts
            WHERE id = $1::INTEGER
            LIMIT 1
        '''
        
        async with get_pg_connection(operation="select") as connection:

            start = time.perf_counter()
            row = await connection.fetchrow(query, id)
            duration = time.perf_counter() - start

            DB_QUERY_DURATION.labels(operation="select").observe(duration)
            
            if row:
                return dict(row)
            
            raise UnauthorizedError()
    
    async def select_by_seller_id(self, seller_id: int) -> Mapping[str, Any]:
        query = '''
            SELECT *
            FROM accounts
            WHERE seller_id = $1::INTEGER
            ORDER BY created_at DESC
            LIMIT 1
        '''
        
        async with get_pg_connection(operation="select") as connection:

            start = time.perf_counter()
            row = await connection.fetchrow(query, seller_id)
            duration = time.perf_counter() - start
            DB_QUERY_DURATION.labels(operation="select").observe(duration)

            if row:
                return dict(row)
            
            raise SellerNotFoundError()
    
    async def select_accounts_by_seller_id(self, seller_id: int) -> Mapping[str, Any]:
        query = '''
            SELECT *
            FROM accounts
            WHERE seller_id = $1::INTEGER
            ORDER BY created_at DESC
        '''
        
        async with get_pg_connection(operation="select") as connection:

            start = time.perf_counter()
            rows = await connection.fetch(query, seller_id)
            duration = time.perf_counter() - start
            DB_QUERY_DURATION.labels(operation="select").observe(duration)

            return [dict(row) for row in rows]
            
    
    async def select_by_login_and_password(self, login: str, password: str) -> Mapping[str, Any]:
        query = '''
            SELECT *
            FROM accounts
            WHERE
                login = $1::TEXT
                AND password = $2::TEXT
            LIMIT 1
        '''

        async with get_pg_connection(operation="select") as connection:

            start = time.perf_counter()
            row = await connection.fetchrow(query, login, password)
            duration = time.perf_counter() - start

            DB_QUERY_DURATION.labels(operation="select").observe(duration)

            if row:
                return dict(row)
            
            raise UnauthorizedError()
    
    async def select_by_login(self, login: str) -> Mapping[str, Any]:
        query = '''
            SELECT *
            FROM accounts
            WHERE
                login = $1::TEXT
            LIMIT 1
        '''

        async with get_pg_connection(operation="select") as connection:

            start = time.perf_counter()
            row = await connection.fetchrow(query, login)
            duration = time.perf_counter() - start

            DB_QUERY_DURATION.labels(operation="select").observe(duration)

            if row:
                return dict(row)
            
            raise UnauthorizedError()
    
    
    async def select_many(self) -> Sequence[Mapping[str, Any]]:
        query = '''
            SELECT *
            FROM accounts
            ORDER BY created_at DESC
        '''
        
        async with get_pg_connection(operation="select") as connection:

            start = time.perf_counter()
            rows = await connection.fetch(query)
            duration = time.perf_counter() - start

            DB_QUERY_DURATION.labels(operation="select").observe(duration)

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
            UPDATE accounts
            SET {fields_str}
            WHERE id = $1::INTEGER
            RETURNING *
        '''

        async with get_pg_connection(operation="update") as connection:

            start = time.perf_counter()
            row = await connection.fetchrow(query, id, *args)
            duration = time.perf_counter() - start

            DB_QUERY_DURATION.labels(operation="update").observe(duration)

            if row:
                return dict(row)
            
            raise UnauthorizedError()

class CustomJSONEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, (datetime, date)):
            return obj.isoformat()
        return super().default(obj)
       
@dataclass(frozen=True)
class AccountRedisStorage:

    # TTL выбран равным 14 дням исходя из следующих соображений:
    # 1. Результаты модерации объявлений редко меняются: после проверки объявление
    #    остаётся в том же статусе, если только владелец не отредактирует его, 
    #    или статус продавца не поменяется,
    #    редактирование происходит нечасто, поэтому данные можно кэшировать надолго
    # 2. Увеличение TTL до 14 дней значительно снижает нагрузку на БД для повторных
    #    запросов одного и того же объявления

    _TTL: timedelta = timedelta(days=14)
    
    ACCOUNT_PREFIX = "account:"
    SELLER_PREFIX = "seller:"

    async def set_latest_by_account_id(self, id: int, row: Mapping[str, Any]) -> None:

        async with get_redis_connection() as connection:
            pipeline = connection.pipeline()
            pipeline.set(
                name=f"{self.ACCOUNT_PREFIX}{id}",
                value=dumps(row, cls=CustomJSONEncoder),
            )
            pipeline.expire(f"{self.ACCOUNT_PREFIX}{id}", self._TTL)
            await pipeline.execute()
    
    async def set_by_seller_id(self, seller_id: int, row: Mapping[str, Any]) -> None:
        async with get_redis_connection() as connection:
            pipeline = connection.pipeline()
            pipeline.set(
                name=f"{self.SELLER_PREFIX}{seller_id}",
                value=dumps(row, cls=CustomJSONEncoder),
            )
            pipeline.expire(f"{self.SELLER_PREFIX}{seller_id}", self._TTL)
            await pipeline.execute()
    
    async def get_latest_by_account_id(self, id: int) -> Mapping[str, Any] | None:

        async with get_redis_connection() as connection:
            row = await connection.get(f"{self.ACCOUNT_PREFIX}{id}")

            if row:
                return loads(row)
            
            return None
    
    async def get_by_seller_id(self, seller_id: int) -> Mapping[str, Any] | None:
        async with get_redis_connection() as connection:
            row = await connection.get(f"{self.SELLER_PREFIX}{seller_id}")

            if row:
                return loads(row)
            
            return None

    async def delete_by_seller_id(self, seller_id: int) -> None:
        async with get_redis_connection() as connection:
            await connection.delete(f"{self.SELLER_PREFIX}{seller_id}")
    
    async def delete_latest_by_account_id(self, id: int) -> None:
        async with get_redis_connection() as connection:
            await connection.delete(f"{self.ACCOUNT_PREFIX}{id}")

@dataclass(frozen=True)
class AccountRepository:

    account_storage: AccountPostgresStorage = AccountPostgresStorage()
    account_redis_storage: AccountRedisStorage = AccountRedisStorage()
    
    
    async def create(self, 
                    login: str,
                    password: str,
                    seller_id: int,
                    is_blocked: bool) -> AccountModel:

        salt = generate_salt()
        stored_password = hash_password(password=password, salt=salt)

        raw_account = await self.account_storage.create(
                        login=login,
                        password=stored_password,
                        salt=salt,
                        seller_id=seller_id,
                        is_blocked=is_blocked
                    )
        
        return AccountModel(**raw_account)
    
    async def get_by_id(self, id: int) -> AccountModel:

        raw_account = await self.account_redis_storage.get_latest_by_account_id(id)

        if raw_account:
            return AccountModel(**raw_account)
        
        raw_account = await self.account_storage.select_by_id(id)

        if raw_account:
            await self.account_redis_storage.set_latest_by_account_id(id, raw_account)
            await self.account_redis_storage.set_by_seller_id(raw_account['seller_id'], raw_account)

        return AccountModel(**raw_account)
    
    async def get_by_seller_id(self, seller_id: int) -> AccountModel:

        raw_account = await self.account_redis_storage.get_by_seller_id(seller_id)

        if raw_account:
            return AccountModel(**raw_account)
        
        raw_account = await self.account_storage.select_by_seller_id(seller_id)
        
        if raw_account:
            await self.account_redis_storage.set_by_seller_id(seller_id, raw_account)
            await self.account_redis_storage.set_latest_by_account_id(raw_account['id'], raw_account)

        return AccountModel(**raw_account)
    
    async def get_by_login_and_password(self, login: str, password: str) -> AccountModel:
        raw_account = await self.account_storage.select_by_login(login)
        hashed_password = raw_account['password']
        salt = raw_account['salt']
        
        if not verify_password(password, hashed_password, salt):
            raise UnauthorizedError()
        
        return AccountModel(**raw_account)  
    
    async def block(self, id: int) -> AccountModel:
        raw_account = await self.account_storage.update(id, is_blocked=True)

        account_model = AccountModel(**raw_account)

        await self.account_redis_storage.set_latest_by_account_id(account_model.id, raw_account)
        await self.account_redis_storage.set_by_seller_id(account_model.seller_id, raw_account)

        return AccountModel(**raw_account)

    async def update_password(self, account_id: int, new_password: str) -> AccountModel:
        
        salt = generate_salt()
        hashed_password = hash_password(new_password, salt)
        
        raw_account = await self.account_storage.update(
            account_id,
            password=hashed_password,
            salt=salt
        )
        
        account_model = AccountModel(**raw_account)

        await self.account_redis_storage.set_latest_by_account_id(account_model.id, raw_account)
        await self.account_redis_storage.set_by_seller_id(account_model.seller_id, raw_account)
        
        return account_model
    
    async def delete(self, id: int) -> AccountModel:
        raw_account = await self.account_storage.delete(id)
        await self.account_redis_storage.delete_latest_by_account_id(id)
        return AccountModel(**raw_account)
    

    async def delete_all_by_seller_id(self, seller_id: int) -> None:

        accounts = await self.account_storage.select_accounts_by_seller_id(seller_id)
        
        if not accounts:
            logger.info(f"No accounts found for seller_id={seller_id}")
            return
        
        for account in accounts:
            await self.delete(account['id'])
        
        logger.info(f"Deleted cache and accounts for seller_id={seller_id}, {len(accounts)} accounts affected")

    
    async def invalidate_by_account_id(self, account_id: int) -> None:

        latest = await self.get_by_id(account_id)
        
        if latest:
            await self.account_redis_storage.delete_by_seller_id(latest.seller_id)
            await self.account_redis_storage.delete_latest_by_account_id(account_id)
            await self.account_storage.delete(account_id)
            logger.info(f"Cache invalidated for account_id={account_id}, seller_id={latest.seller_id}")

    
    async def invalidate_by_seller_id(self, seller_id: int) -> None:
        
        accounts = await self.account_storage.select_accounts_by_seller_id(seller_id)
        
        if not accounts:
            logger.info(f"No accounts found for seller_id={seller_id}")
            return
        
        for account in accounts:
            await self.invalidate_by_account_id(account['id'])
        
        logger.info(f"Invalidated cache for seller_id={seller_id}, {len(accounts)} accounts affected")

    
    async def get_many(self) -> Sequence[AccountModel]:
        return [
            AccountModel(**raw_user)
            for raw_user
            in await self.account_storage.select_many()
        ]