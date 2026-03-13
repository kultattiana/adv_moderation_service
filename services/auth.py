from dataclasses import dataclass
from models.seller import SellerModel
from models.account import AccountModel
from typing import Mapping
from typing import Sequence
from typing import Any
from repositories.sellers import SellerRepository
from repositories.accounts import AccountRepository
from errors import SellerNotFoundError, UnauthorizedError, AccountBlockedError
import jwt
from datetime import datetime, timedelta
from repositories.accounts import AccountRepository
from contextlib import suppress



@dataclass(frozen=True)
class AuthService:

    seller_repo: SellerRepository = SellerRepository()
    account_repo: AccountRepository = AccountRepository()

    _SECRET = 'secret_for_token'
    _USER_TOKEN_TTL = timedelta(days=1)
    _REFRESH_USER_TOKEN_TTL = timedelta(days=2)

    async def login(self, login: str, password: str) -> tuple[str, SellerModel]:
        try:

            account = await self.account_repo.get_by_login_and_password(login, password)
            seller = await self.seller_repo.get_by_seller_id(account.seller_id)
            
            if account.is_blocked:
                raise AccountBlockedError()

            user_token = self._build_user_token(seller, account)
    
            return user_token, seller
        
        except UnauthorizedError:
            raise UnauthorizedError()
        except jwt.InvalidSignatureError as e:
            raise UnauthorizedError()



    async def verify(self, user_token: str) -> SellerModel:
        user_payload = {}
        
        with suppress(Exception):
            user_payload = self._parse_token(user_token)
        
        if raw_expired_at := user_payload.get('expired_at', None):
            if datetime.fromisoformat(raw_expired_at) < datetime.now():
                raise UnauthorizedError()
        
        if seller_id := user_payload.get('seller_id'):
            try:
        
                account_id = user_payload.get('account_id')
                account = await self.account_repo.get_by_id(account_id)

                if account.is_blocked:
                    raise AccountBlockedError()
                
                seller = await self.seller_repo.get_by_seller_id(seller_id)
                
                return seller
                
            except UnauthorizedError as e:
                raise UnauthorizedError()
            except SellerNotFoundError as e:
                raise UnauthorizedError()
            except jwt.InvalidSignatureError as e:
                raise UnauthorizedError()
        
        raise UnauthorizedError()

    
    def _build_user_token(self, seller: SellerModel, account: AccountModel) -> str:

        user_payload = dict(
            seller_id=seller.seller_id,
            username=seller.username,
            email=seller.email,
            account_id = account.id,
            is_verified=seller.is_verified,
            is_blocked=account.is_blocked,
            expired_at=(datetime.now() + self._USER_TOKEN_TTL).isoformat(),
        )

        return self._build_token(user_payload)

    def _build_token(self, payload: Mapping[str, Any]) -> str:
        return jwt.encode(
            payload=payload,
            key=self._SECRET,
            algorithm='HS256',
        )

    def _parse_token(self, token: str) -> Mapping[str, Any]:
        return jwt.decode(
            jwt=token,
            key=self._SECRET,
            algorithms=['HS256'],
        )