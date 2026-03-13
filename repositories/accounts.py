from dataclasses import dataclass
from typing import Mapping, Any, Sequence, Optional, Dict
from clients.postgres import get_pg_connection
from errors import SellerNotFoundError, UnauthorizedError
from models.account import AccountModel
from repositories.moderations import ModerationRepository
from datetime import datetime, timezone
from utils.hash import generate_salt, verify_password, hash_password


@dataclass(frozen = True)
class AccountPostgresStorage:

    async def create(self, 
        login: str,
        password: str,
        seller_id: int,
        is_blocked: bool)-> Mapping[str, Any]:

        query = ''' INSERT INTO accounts (login, password, seller_id, is_blocked)
                    VALUES ($1, $2, $3, $4)
                    RETURNING *
                '''
        
        async with get_pg_connection(operation="insert") as connection:
            return dict(await connection.fetchrow(
                query, login, password, seller_id, is_blocked
            ))
    

    async def delete(self, id: int) -> Mapping[str, Any]:
        query = '''
            DELETE FROM accounts
            WHERE id = $1::INTEGER
            RETURNING *
        '''
        
        async with get_pg_connection(operation="delete") as connection:
            row = await connection.fetchrow(query, id)
            
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
            row = await connection.fetchrow(query, id)
            
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
            row = await connection.fetchrow(query, seller_id)
            
            if row:
                return dict(row)
            
            raise SellerNotFoundError()
    
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
            row = await connection.fetchrow(query, login, password)

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
            row = await connection.fetchrow(query, login)

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
            UPDATE accounts
            SET {fields_str}
            WHERE id = $1::INTEGER
            RETURNING *
        '''

        async with get_pg_connection(operation="update") as connection:
            row = await connection.fetchrow(query, id, *args)

            if row:
                return dict(row)
            
            raise UnauthorizedError()
        

@dataclass(frozen=True)
class AccountRepository:

    account_storage: AccountPostgresStorage = AccountPostgresStorage()
    
    
    async def create(self, 
                    login: str,
                    password: str,
                    seller_id: int,
                    is_blocked: bool) -> AccountModel:
        
        salt = generate_salt()
        hashed_password = hash_password(password=password, salt=salt)
        stored_password = f"{hashed_password}:{salt}"

        raw_account = await self.account_storage.create(
                        login=login,
                        password=stored_password,
                        seller_id=seller_id,
                        is_blocked=is_blocked
                    )
        
        return AccountModel(**raw_account)
    
    async def get_by_id(self, id: int) -> AccountModel:
        raw_account = await self.account_storage.select_by_id(id)
        return AccountModel(**raw_account)
    
    async def get_by_seller_id(self, seller_id: int) -> AccountModel:
        raw_account = await self.account_storage.select_by_seller_id(seller_id)
        return AccountModel(**raw_account)
    
    async def get_by_login_and_password(self, login: str, password: str) -> AccountModel:
        raw_account = await self.account_storage.select_by_login(login)
        stored_password = raw_account['password']

        if ':' in stored_password:
            hashed, salt = stored_password.split(':', 1)
        else:
            hashed, salt = stored_password, None
        
        if not verify_password(password, hashed, salt):
            raise UnauthorizedError()
        
        return AccountModel(**raw_account)  
    
    async def block(self, id: int) -> AccountModel:
        raw_account = await self.account_storage.update(id, is_blocked=True)
        return AccountModel(**raw_account)

    async def update_password(self, account_id: int, new_password: str) -> AccountModel:
        
        salt = generate_salt()
        hashed_password = hash_password(new_password, salt)
        stored_password = f"{hashed_password}:{salt}"
        
        raw_account = await self.account_storage.update(
            account_id,
            password=stored_password
        )
        
        return AccountModel(**raw_account)

    async def delete(self, id: int) -> AccountModel:
        raw_account = await self.account_storage.delete(id)
        return AccountModel(**raw_account)
    
    async def get_many(self) -> Sequence[AccountModel]:
        return [
            AccountModel(**raw_user)
            for raw_user
            in await self.account_storage.select_many()
        ]