import sys
sys.path.append('.')
from typing import Any, Mapping, Generator
import pytest
from fastapi.testclient import TestClient
from main import app
from http import HTTPStatus
import os
import uuid


@pytest.fixture
def app_client() -> Generator[TestClient, None, None]:
    return TestClient(app)


@pytest.fixture
def valid_ad_data():
    return {
        "seller_id": 123,
        "is_verified_seller": True,
        "item_id": 456,
        "name": "Test Product",
        "description": "Test Description",
        "category": 5,
        "images_qty": 3
    }

@pytest.fixture
def seller_data() -> Mapping[str, Any]:
    unique_id = str(uuid.uuid4())[:8]
    return {
        'username': f'Иванов В.П. {unique_id}',
        'email': f'ivanovvp_{unique_id}@mail.ru',
        'password': f'password123_{unique_id}'
    }

@pytest.fixture
def item_data() -> Mapping[str, Any]:
    unique_id = str(uuid.uuid4())[:8]
    return {
        'name': f'Товар 1 {unique_id}',
        'description': f'Стандартный',
        'category': 0,
        'images_qty': 5
    }

@pytest.fixture
def item_zero_images() -> Mapping[str, Any]:
    unique_id = str(uuid.uuid4())[:8]
    return {
        'name': f'Товар 2 {unique_id}',
        'description': f'Стандартный',
        'category': 0,
        'images_qty': 0
    }

@pytest.fixture
def created_seller(app_client: TestClient, seller_data: Mapping[str, Any]):
    response = app_client.post('/sellers/', json=seller_data)
    assert response.status_code == HTTPStatus.CREATED
    seller = response.json()
    yield seller
    app_client.delete(
        f'/sellers/{seller["seller_id"]}',
        cookies={'x-user-id': str(seller['seller_id'])}

    )

@pytest.fixture
def logged_seller(app_client: TestClient, created_seller: dict) -> dict:

    login_data = {
            'email': created_seller['email'],
            'password': created_seller['password']
        }
        
    response = app_client.post('/login', json=login_data)
    assert response.status_code == HTTPStatus.OK
    return created_seller


@pytest.fixture
def verified_seller(app_client: TestClient, logged_seller: dict) -> dict:
    app_client.patch(
        f'/sellers/verify/{logged_seller["seller_id"]}',
        cookies={'x-user-id': str(logged_seller['seller_id'])}
    )
    return logged_seller



@pytest.fixture
def created_item(app_client: TestClient, item_data: Mapping[str, Any], logged_seller: Mapping[str, any]):
    response = app_client.post('/ads/', json=item_data)
    assert response.status_code == HTTPStatus.CREATED
    item = response.json()
    yield item
    app_client.delete(
        f'/ads/{item["item_id"]}',
        cookies={'x-user-id': str(logged_seller['seller_id'])}
    )

@pytest.fixture
def created_item_zero_images(app_client: TestClient, item_zero_images: Mapping[str, Any], logged_seller: Mapping[str, any]):
    response = app_client.post('/ads/', json=item_zero_images)
    assert response.status_code == HTTPStatus.CREATED
    item = response.json()
    yield item
    app_client.delete(
        f'/ads/{item["item_id"]}',
        cookies={'x-user-id': str(logged_seller['seller_id'])}
    )
