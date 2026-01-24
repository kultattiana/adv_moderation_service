import sys
sys.path.append('.')
import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, AsyncMock
from main import app
from routers.predict import adv_service



class TestPositiveCases:
    """Тесты положительных результатов предсказания"""
    
    @pytest.mark.parametrize("test_data,expected_result", [
        ({}, True),
        ({"images_qty": 0}, True),
        ({"is_verified_seller": False}, True),
    ])
    def test_positive_scenarios(self, app_client, valid_ad_data, test_data, expected_result):
        data = {**valid_ad_data, **test_data}
        response = app_client.post("/predict", json=data)
        
        assert response.status_code == 200
        assert response.json() == expected_result


class TestNegativeCases:
    """Тесты отрицательных результатов предсказания"""
    
    def test_unverified_seller_without_images(self, app_client, valid_ad_data):
        data = {**valid_ad_data, "is_verified_seller": False, "images_qty": 0}
        response = app_client.post("/predict", json=data)
        
        assert response.status_code == 200
        assert response.json() == False


class TestValidation:
    """Тесты валидации входных данных"""
    
    @pytest.mark.parametrize("field,invalid_value,error_message", [
        ("seller_id", None, "seller_id is required"),
        ("seller_id", "not_a_number", "seller_id must be integer"),
        ("seller_id", -1, "seller_id must be positive"),
        ("category", 10001, "category must be between 0 and 1000"),
        ("images_qty", -1, "images_qty must be between 0 and 20"),
        ("images_qty", 21, "images_qty must be between 0 and 20"),
        ("name", "", "name must not be empty"),
        ("name", "a" * 10001, "name too long"),
        ("description", "", "description must not be empty"),
    ])
    def test_invalid_inputs(self, app_client, valid_ad_data, field, invalid_value, error_message):
        data = valid_ad_data.copy()
        data[field] = invalid_value
        
        response = app_client.post("/predict", json=data)
        assert response.status_code == 422


class TestEdgeCases:
    """Тесты граничных случаев"""
    
    @pytest.mark.parametrize("test_name,test_data", [
        (
            "minimum_values",
            {
                "seller_id": 1,
                "is_verified_seller": False,
                "item_id": 1,
                "name": "a",
                "description": "b",
                "category": 0,
                "images_qty": 0
            }
        ),
        (
            "maximum_values",
            {
                "seller_id": 999999,
                "is_verified_seller": True,
                "item_id": 999999,
                "name": "a" * 500,
                "description": "b" * 10000,
                "category": 1000,
                "images_qty": 20
            }
        ),
    ])
    def test_edge_scenarios(self, app_client, valid_ad_data, test_name, test_data):
        data = {**valid_ad_data, **test_data}
        response = app_client.post("/predict", json=data)
        
        assert response.status_code == 200


class TestMissingFields:
    """Тесты отсутствующих обязательных полей"""
    
    @pytest.mark.parametrize("missing_field", [
        "seller_id",
        "is_verified_seller",
        "item_id",
        "name",
        "description",
        "category",
        "images_qty"
    ])
    def test_missing_required_field(self, app_client, valid_ad_data, missing_field):
        data = valid_ad_data.copy()
        del data[missing_field]
        
        response = app_client.post("/predict", json=data)
        assert response.status_code == 422


def test_business_logic_error_handling(app_client, valid_ad_data):
    """Тест обработки ошибок бизнес-логики"""
    
    with patch.object(adv_service, 'predict', 
                     AsyncMock(side_effect=ValueError('Simulated business logic error'))):
        response = app_client.post("/predict", json=valid_ad_data)
        
        assert response.status_code == 500
        response_data = response.json()
        assert "Internal server error" in response_data["detail"]
        assert "Simulated business logic error" in response_data["detail"]