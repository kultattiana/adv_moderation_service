import pytest
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, Mock, patch
from services.auth import AuthService

from fastapi import FastAPI, Depends, Request
from fastapi.testclient import TestClient
from typing import Annotated
from pydantic import BaseModel
from http import HTTPStatus

from dataclasses import dataclass
from models.seller import SellerModel
from models.account import AccountModel
from repositories.sellers import SellerRepository
from repositories.accounts import AccountRepository
from errors import SellerNotFoundError, UnauthorizedError, AccountBlockedError
from freezegun import freeze_time
import jwt


@pytest.mark.asyncio
class TestAuthUnit:

    async def test_successful_login(self, created_seller_data, created_account):

        seller_repo = AsyncMock()
        account_repo = AsyncMock()

        auth_service = AuthService(account_repo=account_repo, seller_repo=seller_repo)
        
        account_repo.get_by_login_and_password.return_value = AccountModel(**created_account)
        seller_repo.get_by_seller_id.return_value = SellerModel(**created_seller_data)

        user_token, seller = await auth_service.login(created_account["login"], created_account["password"])

        assert seller.seller_id == created_seller_data["seller_id"]
        assert user_token is not None
        account_repo.get_by_login_and_password.assert_called_once_with(created_account["login"], created_account["password"])
        seller_repo.get_by_seller_id.assert_called_once_with(created_seller_data["seller_id"])

    async def test_login_with_blocked_account(self, created_seller_data, created_account):
        
        seller_repo = AsyncMock()
        account_repo = AsyncMock()

        auth_service = AuthService(account_repo=account_repo, seller_repo=seller_repo)

        created_account['is_blocked'] = True
        account_repo.get_by_login_and_password.return_value = AccountModel(**created_account)
        seller_repo.get_by_seller_id.return_value = SellerModel(**created_seller_data)

        with pytest.raises(AccountBlockedError):
            await auth_service.login(created_account["login"], created_account["password"])
        
        created_account['is_blocked'] = False


    async def test_successful_verification(self, created_seller_data):

        seller_repo = AsyncMock()
        seller_repo.get_by_seller_id.return_value = SellerModel(**created_seller_data)

        auth_service = AuthService(seller_repo=seller_repo)
        
        valid_token = auth_service._build_user_token(
            SellerModel(**created_seller_data),
            AccountModel(id=1, seller_id=1, login="test", password="test", is_blocked=False)
        )


        seller = await auth_service.verify(valid_token)

        assert seller.seller_id == created_seller_data['seller_id']
        assert seller.username == created_seller_data['username']
        assert seller.email == created_seller_data['email']
        assert seller.is_verified == created_seller_data['is_verified']
        assert seller.password == created_seller_data['password']


    @freeze_time("2026-01-01 12:00:00")
    async def test_verification_with_expired_token(self, created_seller_data):

        seller_repo = AsyncMock()
        seller_repo.get_by_seller_id.return_value = SellerModel(**created_seller_data)

        auth_service = AuthService(seller_repo=seller_repo)
        
        account = AccountModel(id=1, seller_id=1, login="test", password="test", is_blocked=False)

        original_ttl = auth_service._USER_TOKEN_TTL

        try:
            object.__setattr__(auth_service, '_USER_TOKEN_TTL', timedelta(days=-1))
            expired_token = auth_service._build_user_token(SellerModel(**created_seller_data), account)
        finally:
            object.__setattr__(auth_service, '_USER_TOKEN_TTL', original_ttl)

        with pytest.raises(UnauthorizedError):
            await auth_service.verify(expired_token)

    async def test_verification_with_blocked_account_in_token(self, created_seller_data):

        seller_repo = AsyncMock()
        seller_repo.get_by_seller_id.return_value = SellerModel(**created_seller_data)

        auth_service = AuthService(seller_repo=seller_repo)
        
        blocked_account = AccountModel(id=1, seller_id=1, login="test", password="test", is_blocked=True)
        token_with_blocked = auth_service._build_user_token(SellerModel(**created_seller_data), blocked_account)

        with pytest.raises(AccountBlockedError):
            await auth_service.verify(token_with_blocked)

    async def test_verification_with_nonexistent_seller(self, created_seller_data):
        
        seller_repo = AsyncMock()
        auth_service = AuthService(seller_repo=seller_repo)

        account = AccountModel(id=1, seller_id=999, login="test", password="test", is_blocked=False)
        token = auth_service._build_user_token(SellerModel(**created_seller_data), account)

        seller_repo.get_by_seller_id.side_effect = SellerNotFoundError()

        with pytest.raises(UnauthorizedError):
            await auth_service.verify(token)

    async def test_verification_with_invalid_token(self, auth_service: AuthService):
        
        with pytest.raises(UnauthorizedError):
            await auth_service.verify("invalid.token.string")
    

    def test_build_user_token(self, auth_service: AuthService, created_seller_data):
    
        account = AccountModel(id=1, seller_id=1, login="test", password="test", is_blocked=False)

        with freeze_time("2024-01-01 12:00:00"):
            token = auth_service._build_user_token(SellerModel(**created_seller_data), account)

            payload = auth_service._parse_token(token)

            assert payload["seller_id"] == created_seller_data['seller_id']
            assert payload["username"] == created_seller_data['username']
            assert payload["email"] == created_seller_data['email']
            assert payload["account_id"] == 1
            assert payload["is_verified"] == created_seller_data['is_verified']
            assert payload["is_blocked"] is False
            assert payload["expired_at"] == "2024-01-02T12:00:00"
    
    def test_parse_token_with_invalid_signature(self, auth_service):
        
        invalid_token = jwt.encode(
            payload={"test": "data"},
            key="wrong_secret",
            algorithm='HS256'
        )

        with pytest.raises(jwt.InvalidSignatureError):
            auth_service._parse_token(invalid_token)
    

@pytest.mark.integration
class TestMiddlewareAuthIntegration:

    def test_protected_endpoint_requires_auth(self, app_client):
    
        mock_auth_service = AsyncMock()
        
        mock_auth_service.verify = AsyncMock(side_effect=UnauthorizedError("No token"))
        
        response = app_client.post(
            "/async_predict/123",
            json={"data": "test"}
        )
        
        assert response.status_code == HTTPStatus.UNAUTHORIZED




