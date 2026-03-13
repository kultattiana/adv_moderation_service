from typing import Any, Mapping
import pytest
from fastapi.testclient import TestClient
from http import HTTPStatus
from unittest.mock import AsyncMock, patch
import uuid
from repositories.sellers import SellerRepository
from repositories.accounts import AccountRepository
from services.sellers import SellerService
from services.auth import AuthService
from dependencies import seller_service, auth_service
from models.seller import SellerModel
from models.account import AccountModel

PASSWORD = 'qwerty'

@pytest.mark.integration
class TestSellerAPI:
    
    def test_create_seller(self, seller_data: Mapping[str, Any], app_client: TestClient):
        response = app_client.post('/sellers/', json=seller_data)
        assert response.status_code == HTTPStatus.CREATED
        
        seller = response.json()
        assert seller['username'] == seller_data['username']
        assert seller['email'] == seller_data['email']
        assert seller['password'] == seller_data['password']
        assert seller['is_verified'] == False

        response = app_client.post('/sellers/', json=seller_data)
        assert response.status_code == HTTPStatus.BAD_REQUEST
        
        app_client.delete(
            f'/sellers/{seller["seller_id"]}',
            cookies={'x-user-id': str(seller['seller_id'])}
        )
    
    def test_verify_seller(self, app_client: TestClient, created_seller: dict, x_user_token: str):
        response = app_client.patch(
            f'/sellers/verify/{created_seller["seller_id"]}',
            cookies={'x-user-token': x_user_token}
        )
        
        assert response.status_code == HTTPStatus.OK
        
        updated_seller = response.json()
        assert updated_seller['seller_id'] == created_seller['seller_id']
        assert updated_seller['is_verified'] == True
    
    def test_delete_seller(self, app_client: TestClient, created_seller: dict, x_user_token: str):
        response = app_client.delete(
            f'/sellers/{created_seller["seller_id"]}',
            cookies={'x-user-token': x_user_token}
        )
        
        assert response.status_code == HTTPStatus.OK
        
        deleted_seller = response.json()
        assert deleted_seller['seller_id'] == created_seller['seller_id']
        
        get_response = app_client.get(f'/sellers/{deleted_seller["seller_id"]}')
        assert get_response.status_code == HTTPStatus.NOT_FOUND
    
    def test_get_many_sellers(self, app_client: TestClient, created_seller: dict):
        response = app_client.get('/sellers')
        assert response.status_code == HTTPStatus.OK
        
        sellers = response.json()
        seller_ids = [seller['seller_id'] for seller in sellers]
        assert created_seller['seller_id'] in seller_ids
    
    def test_login_seller(self, app_client: TestClient, created_seller: dict, auth_service: AuthService):
        login_data = {
            'login': created_seller['username'],
            'password': created_seller['password']
        }
        
        response = app_client.post('/login', json=login_data)
        
        assert response.status_code == HTTPStatus.OK
        x_user_token = response.cookies.get('x-user-token')
        assert x_user_token is not None
        user_payload = auth_service._parse_token(x_user_token)

        assert user_payload.get('seller_id') == created_seller['seller_id']
        
        logged_user = response.json()
        assert logged_user['seller_id'] == created_seller['seller_id']
    
    def test_get_current_seller(self, app_client: TestClient, created_seller: dict, x_user_token):
        response = app_client.get(
            '/sellers/current/',
            cookies={'x-user-token': x_user_token}
        )
        
        assert response.status_code == HTTPStatus.OK
        
        seller = response.json()
        assert seller['seller_id'] == created_seller['seller_id']
    
    def test_get_by_seller_id(self, app_client: TestClient, created_seller: dict):
        response = app_client.get(f'/sellers/{created_seller["seller_id"]}')
        assert response.status_code == HTTPStatus.OK
        
        seller = response.json()
        assert seller['seller_id'] == created_seller['seller_id']


class TestSellerAPIUnit:
    
    def test_create_seller_unit(self, app_client_with_mocks, seller_data, mock_seller_storage, created_account):
        mock_account_storage = AsyncMock()
        mock_account_repo = AccountRepository(account_storage=mock_account_storage)

        mock_moderation_repo = AsyncMock()
        mock_seller_repo = SellerRepository(seller_storage=mock_seller_storage, moderation_repo=mock_moderation_repo, 
                                            account_repo=mock_account_repo)
        mock_seller_service = SellerService(seller_repo=mock_seller_repo)

        app_client_with_mocks.app.dependency_overrides[seller_service] = lambda: mock_seller_service
        mock_account_storage.create.return_value = created_account

        mock_seller_storage.create.return_value = {
            'seller_id': 1,
            **seller_data,
            'is_verified': False
        }
        
        response = app_client_with_mocks.post('/sellers/', json=seller_data)
        
        assert response.status_code == HTTPStatus.CREATED
        mock_seller_storage.create.assert_called_once()
        mock_account_storage.create.assert_called_once()
    
    
    def test_verify_seller_unit(self, app_client_with_mocks, mock_seller_storage, 
                                created_seller_data, override_auth_unit, x_user_token_unit):

        mock_moderation_repo = AsyncMock()
        mock_seller_repo = SellerRepository(seller_storage=mock_seller_storage, moderation_repo=mock_moderation_repo)
        mock_seller_service = SellerService(seller_repo=mock_seller_repo)

        app_client_with_mocks.app.dependency_overrides[seller_service] = lambda: mock_seller_service
        verified_seller = {**created_seller_data, 'is_verified': True}
        mock_seller_storage.update.return_value = verified_seller
        
        response = app_client_with_mocks.patch(
            f'/sellers/verify/{created_seller_data["seller_id"]}',
            cookies={'x-user-token': x_user_token_unit}
        )
        
        assert response.status_code == HTTPStatus.OK
        assert response.json()['is_verified'] == True
        mock_seller_storage.update.assert_called_once()
        mock_moderation_repo.invalidate_by_seller_id.assert_called_once()
    
    def test_delete_seller_unit(self, app_client_with_mocks, mock_seller_storage, 
                                created_seller_data, x_user_token_unit, created_account, override_auth_unit):
        
        mock_account_storage = AsyncMock()
        mock_account_repo = AccountRepository(account_storage=mock_account_storage)

        mock_moderation_repo = AsyncMock()
        mock_seller_repo = SellerRepository(seller_storage=mock_seller_storage, moderation_repo=mock_moderation_repo,
                                            account_repo=mock_account_repo)
        mock_seller_service = SellerService(seller_repo=mock_seller_repo)

        app_client_with_mocks.app.dependency_overrides[seller_service] = lambda: mock_seller_service
        mock_seller_storage.delete.return_value = created_seller_data
        
        response = app_client_with_mocks.delete(
            f'/sellers/{created_seller_data["seller_id"]}',
            cookies={'x-user-token': x_user_token_unit}
        )
        
        assert response.status_code == HTTPStatus.OK
        mock_seller_storage.delete.assert_called_once_with(created_seller_data["seller_id"])
        mock_moderation_repo.delete_all_by_seller_id.assert_called_once()

    
    def test_get_many_sellers_unit(self, app_client_with_mocks, mock_seller_storage, created_seller_data):
        mock_moderation_repo = AsyncMock()
        mock_seller_repo = SellerRepository(seller_storage=mock_seller_storage, moderation_repo=mock_moderation_repo)
        mock_seller_service = SellerService(seller_repo=mock_seller_repo)

        app_client_with_mocks.app.dependency_overrides[seller_service] = lambda: mock_seller_service
        mock_seller_storage.select_many.return_value = [created_seller_data]
        
        response = app_client_with_mocks.get('/sellers')
        
        assert response.status_code == HTTPStatus.OK
        sellers = response.json()
        assert len(sellers) == 1
        mock_seller_storage.select_many.assert_called_once()
    
    def test_login_seller_unit(self, app_client_with_mocks, mock_seller_storage,
                               created_seller_data, created_account):
        mock_moderation_repo = AsyncMock()
        mock_account_storage = AsyncMock()

        mock_account_repo = AccountRepository(account_storage = mock_account_storage)
        mock_seller_repo = SellerRepository(seller_storage=mock_seller_storage, moderation_repo=mock_moderation_repo)

        mock_seller_service = SellerService(seller_repo=mock_seller_repo)
        mock_auth_service = AuthService(seller_repo=mock_seller_repo, account_repo=mock_account_repo)

        app_client_with_mocks.app.dependency_overrides[seller_service] = lambda: mock_seller_service
        app_client_with_mocks.app.dependency_overrides[auth_service] = lambda: mock_auth_service
        mock_seller_storage.select_by_seller_id.return_value = created_seller_data
        mock_account_storage.select_by_login.return_value = created_account


        with patch('repositories.accounts.verify_password') as mock_verify:
            mock_verify.return_value = True
        
            login_data = {
                'login': created_seller_data['username'],
                'password': created_seller_data['password']
            }
            
            response = app_client_with_mocks.post('/login', json=login_data)
            
            assert response.status_code == HTTPStatus.OK

            x_user_token = response.cookies.get('x-user-token')

            assert x_user_token is not None
            user_payload = mock_auth_service._parse_token(x_user_token)

            assert user_payload.get('seller_id') == created_seller_data['seller_id']
            mock_account_storage.select_by_login.assert_called_once()
            mock_verify.assert_called_once()
            mock_seller_storage.select_by_seller_id.assert_called_once()
    
    def test_get_current_seller_unit(self, app_client_with_mocks, mock_seller_storage, 
                                     created_seller_data, override_auth_unit, x_user_token_unit):

        mock_moderation_repo = AsyncMock()
        mock_seller_repo = SellerRepository(seller_storage=mock_seller_storage, moderation_repo=mock_moderation_repo)
        mock_seller_service = SellerService(seller_repo=mock_seller_repo)

        app_client_with_mocks.app.dependency_overrides[seller_service] = lambda: mock_seller_service
        mock_seller_storage.select_by_seller_id.return_value = created_seller_data
        
        response = app_client_with_mocks.get(
            '/sellers/current/',
            cookies={'x-user-token': x_user_token_unit}
        )
        
        assert response.status_code == HTTPStatus.OK
        seller = response.json()
        assert seller['seller_id'] == created_seller_data['seller_id']
        mock_seller_storage.select_by_seller_id.assert_called_once()
    
    def test_get_by_seller_id(self, app_client_with_mocks, mock_seller_storage, created_seller_data):

        mock_moderation_repo = AsyncMock()
        mock_seller_repo = SellerRepository(seller_storage=mock_seller_storage, moderation_repo=mock_moderation_repo)
        mock_seller_service = SellerService(seller_repo=mock_seller_repo)

        app_client_with_mocks.app.dependency_overrides[seller_service] = lambda: mock_seller_service
        mock_seller_storage.select_by_seller_id.return_value = created_seller_data
        
        response = app_client_with_mocks.get(f'/sellers/{created_seller_data["seller_id"]}')
        
        assert response.status_code == HTTPStatus.OK
        seller = response.json()
        assert seller['seller_id'] == created_seller_data['seller_id']
        mock_seller_storage.select_by_seller_id.assert_called_once()