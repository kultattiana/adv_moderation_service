from typing import Any, Mapping
import pytest
from fastapi.testclient import TestClient
from http import HTTPStatus
import uuid

PASSWORD = 'qwerty'


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
    
    def test_verify_seller(self, app_client: TestClient, created_seller: dict):
        response = app_client.patch(
            f'/sellers/verify/{created_seller["seller_id"]}',
            cookies={'x-user-id': str(created_seller['seller_id'])}
        )
        
        assert response.status_code == HTTPStatus.OK
        
        updated_seller = response.json()
        assert updated_seller['seller_id'] == created_seller['seller_id']
        assert updated_seller['is_verified'] == True
    
    def test_delete_seller(self, app_client: TestClient, created_seller: dict):
        response = app_client.delete(
            f'/sellers/{created_seller["seller_id"]}',
            cookies={'x-user-id': str(created_seller['seller_id'])}
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
    
    def test_login_seller(self, app_client: TestClient, created_seller: dict):
        login_data = {
            'email': created_seller['email'],
            'password': created_seller['password']
        }
        
        response = app_client.post('/login', json=login_data)
        assert response.status_code == HTTPStatus.OK
        assert response.cookies.get('x-user-id') == str(created_seller['seller_id'])
        
        logged_user = response.json()
        assert logged_user['seller_id'] == created_seller['seller_id']
    
    def test_get_current_seller(self, app_client: TestClient, created_seller: dict):
        response = app_client.get(
            '/sellers/current/',
            cookies={'x-user-id': str(created_seller['seller_id'])}
        )
        
        assert response.status_code == HTTPStatus.OK
        
        seller = response.json()
        assert seller['seller_id'] == created_seller['seller_id']
    
    def test_get_by_seller_id(self, app_client: TestClient, created_seller: dict):
        response = app_client.get(f'/sellers/{created_seller["seller_id"]}')
        assert response.status_code == HTTPStatus.OK
        
        seller = response.json()
        assert seller['seller_id'] == created_seller['seller_id']