import sys
sys.path.append('.')
from typing import Any, Mapping, Generator
import pytest
from fastapi.testclient import TestClient
from main import app
from http import HTTPStatus


@pytest.fixture
def app_client() -> Generator[TestClient, None, None]:
    return TestClient(app)


@pytest.fixture
def valid_ad_data():
    """Фикстура с валидными данными объявления"""
    return {
        "seller_id": 123,
        "is_verified_seller": True,
        "item_id": 456,
        "name": "Test Product",
        "description": "Test Description",
        "category": 5,
        "images_qty": 3
    }
