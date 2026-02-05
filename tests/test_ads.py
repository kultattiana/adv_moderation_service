from typing import Any, Mapping
import pytest
from fastapi.testclient import TestClient
from http import HTTPStatus


class TestAdAPI:

    def test_create_ad(self, logged_seller: dict, item_data: dict,
                             app_client: TestClient):

        response = app_client.post('/ads/', json=item_data)
        assert response.status_code == HTTPStatus.CREATED
        
        created_item = response.json()
        assert created_item['name'] == item_data['name']
        assert created_item['description'] == item_data['description']
        assert created_item['category'] == item_data['category']
        assert created_item['images_qty'] == item_data['images_qty']

    
    def test_update_description(self, app_client: TestClient, created_item: dict, logged_seller: dict):
        new_description = "Better description"
        response = app_client.patch(
            f'/ads/update/{created_item["item_id"]}',
            params={'description': new_description},
            cookies={'x-user-id': str(logged_seller['seller_id'])}
        )
        
        assert response.status_code == HTTPStatus.OK
        
        updated_item = response.json()
        assert updated_item['item_id'] == created_item['item_id']
        assert updated_item['description'] == "Better description"
    
    def test_delete_ad(self, app_client: TestClient, logged_seller:dict, created_item: dict):
        response = app_client.delete(
            f'/ads/{created_item["item_id"]}',
            cookies={'x-user-id': str(logged_seller['seller_id'])}
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
    
    def test_get_by_seller_id(self, app_client: TestClient, created_item: dict, logged_seller: dict):
        response = app_client.get(f'/ads/list/{logged_seller["seller_id"]}')

        items = response.json()
        assert response.status_code == HTTPStatus.OK
        
        item_ids = [item['item_id'] for item in items]
        assert created_item['item_id'] in item_ids