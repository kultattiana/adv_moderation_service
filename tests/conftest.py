import sys
sys.path.append('.')
from typing import Any, Mapping, Generator
import pytest
from fastapi.testclient import TestClient
from main import app
from model import load_model
import os


@pytest.fixture(autouse=True)
def setup_model():
    """Фикстура, которая автоматически запускается перед каждым тестом"""

    temp_model_path = 'test_model.pkl'
    try:
        model = load_model(temp_model_path)
        app.state.model = model
        yield
    finally:
        if os.path.exists(temp_model_path):
            os.remove(temp_model_path)
        app.state.model = None

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
