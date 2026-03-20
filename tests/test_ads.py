from typing import Any, Mapping
import pytest
from fastapi.testclient import TestClient
from http import HTTPStatus
from unittest.mock import AsyncMock, patch
from datetime import datetime
from repositories.ads import AdRepository
from repositories.sellers import SellerRepository
from errors import AdNotFoundError
from services.advertisements import AdvertisementService
from dependencies import ad_service

@pytest.mark.integration
class TestAdAPI:

    def test_create_ad(self, item_data: dict, created_seller: dict,
                             app_client: TestClient, override_auth):

        response = app_client.post('/ads/', json=item_data)
        assert response.status_code == HTTPStatus.CREATED
        
        created_item = response.json()
        assert created_item['name'] == item_data['name']
        assert created_item['description'] == item_data['description']
        assert created_item['category'] == item_data['category']
        assert created_item['images_qty'] == item_data['images_qty']

    
    def test_update_description(self, app_client: TestClient, created_item: dict, 
                                created_seller: dict, override_auth, x_user_token):
        new_description = "Better description"
        response = app_client.patch(
            f'/ads/update/{created_item["item_id"]}',
            params={'description': new_description},
            cookies={'x-user-token': x_user_token}
        )
        
        assert response.status_code == HTTPStatus.OK
        
        updated_item = response.json()
        assert updated_item['item_id'] == created_item['item_id']
        assert updated_item['description'] == "Better description"
    
    def test_delete_ad(self, app_client: TestClient, created_seller:dict, 
                       created_item: dict, override_auth, x_user_token):
        response = app_client.delete(
            f'/ads/{created_item["item_id"]}',
            cookies={'x-user-token': x_user_token}
        )
        
        assert response.status_code == HTTPStatus.OK
        
        deleted_item = response.json()
        assert deleted_item['item_id'] == created_item['item_id']
        
        get_response = app_client.get(f'/ads/{deleted_item["item_id"]}')
        assert get_response.status_code == HTTPStatus.NOT_FOUND
    
    def test_get_many_ads(self, app_client: TestClient, created_item: dict):
        response = app_client.get('/ads')
        assert response.status_code == HTTPStatus.OK
        
        items = response.json()
        item_ids = [item['item_id'] for item in items]
        assert created_item['item_id'] in item_ids
    
    def test_get_by_item_id(self, app_client: TestClient, created_item: dict):
        response = app_client.get(f'/ads/{created_item["item_id"]}')
        assert response.status_code == HTTPStatus.OK
        
        item = response.json()
        assert item['item_id'] == created_item['item_id']
    
    def test_get_by_seller_id(self, app_client: TestClient, created_item: dict, created_seller: dict,
                              ):
        response = app_client.get(f'/ads/list/{created_seller["seller_id"]}')

        items = response.json()
        assert response.status_code == HTTPStatus.OK
        
        item_ids = [item['item_id'] for item in items]
        assert created_item['item_id'] in item_ids
    
    def test_close_ad(self, app_client: TestClient, 
                                 created_item: dict, created_seller: dict,
                                 x_user_token):
        
        response = app_client.patch(
            f'/ads/close/{created_item["item_id"]}',
            cookies={'x-user-token': x_user_token}
        )
        
        assert response.status_code == HTTPStatus.OK
        closed_item = response.json()
        assert closed_item['item_id'] == created_item['item_id']
        assert closed_item['is_closed'] == True
        
        get_response = app_client.get(f'/ads/{created_item["item_id"]}')
        assert get_response.status_code == HTTPStatus.OK
        assert get_response.json()['is_closed'] == True
    
    def test_close_ad_not_found_integration(self, app_client: TestClient, 
                                           created_seller: dict, override_auth, x_user_token):
        
        non_existent_id = 99999
        response = app_client.patch(
            f'/ads/close/{non_existent_id}',
            cookies={'x-user-token': x_user_token}
        )
        
        assert response.status_code == HTTPStatus.NOT_FOUND
        assert f'Item {non_existent_id} is not found' in response.json()['detail']


class TestAdAPIUnit:

    def test_create_ad_unit(self, app_client_with_mocks, item_data,
                            logged_seller_data, mock_ad_storage, mock_seller_storage, override_auth_unit):
        
        mock_seller_repo = SellerRepository(seller_storage=mock_seller_storage)
        
        mock_ad_storage.create.return_value = {
            'item_id': 1,
            **item_data,
            'seller_id': logged_seller_data['seller_id']
        }

        mock_seller_storage.select_by_seller_id.return_value = logged_seller_data

        mock_ad_repo = AdRepository(ad_storage=mock_ad_storage)
        mock_ad_service = AdvertisementService(ad_repo=mock_ad_repo, seller_repo=mock_seller_repo)
        app_client_with_mocks.app.dependency_overrides[ad_service] = lambda: mock_ad_service

        response = app_client_with_mocks.post(
            '/ads/', 
            json=item_data, 
            cookies={'x-user-id': str(logged_seller_data['seller_id'])}
        )
        
        assert response.status_code == HTTPStatus.CREATED
        created_item = response.json()
        assert created_item['name'] == item_data['name']
        
        mock_ad_storage.create.assert_called_once()
        mock_seller_storage.select_by_seller_id.assert_called_once()

    
    def test_update_description_unit(self, app_client_with_mocks,
                                    created_item_data, logged_seller_data, mock_ad_storage, mock_seller_storage, override_auth_unit):
        
        mock_moderation_repo = AsyncMock()
        mock_seller_repo = SellerRepository(seller_storage=mock_seller_storage)
        mock_ad_repo = AdRepository(ad_storage=mock_ad_storage)
        mock_ad_service = AdvertisementService(ad_repo=mock_ad_repo, seller_repo=mock_seller_repo, moderation_repo=mock_moderation_repo)
        
        app_client_with_mocks.app.dependency_overrides[ad_service] = lambda: mock_ad_service

        new_description = "Better description"
        updated_item = {**created_item_data, 'description': new_description}
        mock_ad_storage.select_by_item_id.return_value = created_item_data
        mock_ad_storage.update.return_value = updated_item
        
        response = app_client_with_mocks.patch(
            f'/ads/update/{created_item_data["item_id"]}',
            params={'description': new_description},
            cookies={'x-user-id': str(logged_seller_data['seller_id'])}
        )
        
        assert response.status_code == HTTPStatus.OK
        mock_ad_storage.update.assert_called_once()
        mock_moderation_repo.invalidate_by_item_id.assert_called_once()
    
    def test_delete_ad_unit(self, app_client_with_mocks, mock_ad_storage, mock_seller_storage,
                           created_item_data, logged_seller_data, override_auth_unit):
        
        mock_moderation_repo = AsyncMock()
        mock_seller_repo = SellerRepository(seller_storage=mock_seller_storage)
        mock_ad_repo = AdRepository(ad_storage=mock_ad_storage)
        mock_ad_service = AdvertisementService(ad_repo=mock_ad_repo, seller_repo=mock_seller_repo, moderation_repo=mock_moderation_repo)
        
        app_client_with_mocks.app.dependency_overrides[ad_service] = lambda: mock_ad_service

        mock_ad_storage.select_by_item_id.return_value = created_item_data
        mock_ad_storage.delete.return_value = created_item_data
        
        response = app_client_with_mocks.delete(
            f'/ads/{created_item_data["item_id"]}',
            cookies={'x-user-id': str(logged_seller_data['seller_id'])}
        )
        
        assert response.status_code == HTTPStatus.OK
        mock_ad_storage.delete.assert_called_once()
        mock_moderation_repo.delete_all_by_item_id.assert_called_once()
    
    def test_get_many_ads_unit(self, app_client_with_mocks, mock_ad_storage, mock_seller_storage, created_item_data):

        mock_moderation_repo = AsyncMock()
        mock_seller_repo = SellerRepository(seller_storage=mock_seller_storage)
        mock_ad_repo = AdRepository(ad_storage=mock_ad_storage)
        mock_ad_service = AdvertisementService(ad_repo=mock_ad_repo, seller_repo=mock_seller_repo, moderation_repo=mock_moderation_repo)
        
        app_client_with_mocks.app.dependency_overrides[ad_service] = lambda: mock_ad_service
    
        mock_ad_storage.select_many.return_value = [created_item_data]
        
        response = app_client_with_mocks.get('/ads')
        
        assert response.status_code == HTTPStatus.OK
        mock_ad_storage.select_many.assert_called_once()
    
    def test_get_by_item_id_unit(self, app_client_with_mocks, mock_ad_storage, mock_seller_storage, created_item_data):

        mock_moderation_repo = AsyncMock()
        mock_seller_repo = SellerRepository(seller_storage=mock_seller_storage)
        mock_ad_repo = AdRepository(ad_storage=mock_ad_storage)
        mock_ad_service = AdvertisementService(ad_repo=mock_ad_repo, seller_repo=mock_seller_repo, moderation_repo=mock_moderation_repo)
        
        app_client_with_mocks.app.dependency_overrides[ad_service] = lambda: mock_ad_service
        mock_ad_storage.select_by_item_id.return_value = created_item_data
        
        response = app_client_with_mocks.get(f'/ads/{created_item_data["item_id"]}')
        
        assert response.status_code == HTTPStatus.OK
        mock_ad_storage.select_by_item_id.assert_called_once()
    
    def test_get_by_seller_id_unit(self, app_client_with_mocks, mock_ad_storage, mock_seller_storage,
                                  created_item_data, logged_seller_data):
        
        mock_moderation_repo = AsyncMock()
        mock_seller_repo = SellerRepository(seller_storage=mock_seller_storage)
        mock_ad_repo = AdRepository(ad_storage=mock_ad_storage)
        mock_ad_service = AdvertisementService(ad_repo=mock_ad_repo, seller_repo=mock_seller_repo, moderation_repo=mock_moderation_repo)
        
        app_client_with_mocks.app.dependency_overrides[ad_service] = lambda: mock_ad_service

        mock_ad_storage.select_by_seller_id.return_value = [created_item_data]
        
        response = app_client_with_mocks.get(f'/ads/list/{logged_seller_data["seller_id"]}')
        
        assert response.status_code == HTTPStatus.OK
        mock_ad_storage.select_by_seller_id.assert_called_once()
    
    def test_close_ad_success_unit(self, app_client_with_mocks, 
                                   created_item_data: dict, logged_seller_data: dict,
                                   mock_ad_storage, mock_seller_storage, override_auth_unit):
        closed_item = {
            **created_item_data,
            'is_closed': True
        }

        mock_moderation_repo = AsyncMock()
        mock_seller_repo = SellerRepository(seller_storage=mock_seller_storage)
        mock_ad_repo = AdRepository(ad_storage=mock_ad_storage)
        mock_ad_service = AdvertisementService(ad_repo=mock_ad_repo, seller_repo=mock_seller_repo, moderation_repo=mock_moderation_repo)
        
        app_client_with_mocks.app.dependency_overrides[ad_service] = lambda: mock_ad_service
        
        mock_ad_storage.select_by_item_id.return_value = created_item_data
        mock_ad_storage.update.return_value = closed_item
        response = app_client_with_mocks.patch(
            f'/ads/close/{created_item_data["item_id"]}',
            cookies={'x-user-id': str(logged_seller_data['seller_id'])}
        )
        
        assert response.status_code == HTTPStatus.OK
        response_data = response.json()
        assert response_data['item_id'] == created_item_data['item_id']
        assert response_data['is_closed'] == True
        
        mock_ad_storage.update.assert_called_once()
        mock_moderation_repo.delete_all_by_item_id.assert_called_once()
    
    def test_close_ad_not_found_unit(self, app_client_with_mocks, 
                                     logged_seller_data: dict, mock_ad_storage, mock_seller_storage, override_auth_unit):
        
        mock_moderation_repo = AsyncMock()
        mock_seller_repo = SellerRepository(seller_storage=mock_seller_storage)
        mock_ad_repo = AdRepository(ad_storage=mock_ad_storage)
        mock_ad_service = AdvertisementService(ad_repo=mock_ad_repo, seller_repo=mock_seller_repo, moderation_repo=mock_moderation_repo)
        
        app_client_with_mocks.app.dependency_overrides[ad_service] = lambda: mock_ad_service
        non_existent_id = 99999
        mock_ad_storage.select_by_item_id.side_effect = AdNotFoundError()
        mock_ad_storage.update.side_effect = AdNotFoundError()
        
        response = app_client_with_mocks.patch(
            f'/ads/close/{non_existent_id}',
            cookies={'x-user-id': str(logged_seller_data['seller_id'])}
        )
        
        assert response.status_code == HTTPStatus.NOT_FOUND
        assert f'Item {non_existent_id} is not found' in response.json()['detail']
        
        mock_ad_storage.select_by_item_id.assert_called_once()