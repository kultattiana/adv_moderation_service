import sys
sys.path.append('.')
import pytest
from fastapi.testclient import TestClient
from main import app
from main import predict
import main
import json

client = TestClient(app)


VALID_AD_DATA = {
    "seller_id": 123,
    "is_verified_seller": True,
    "item_id": 456,
    "name": "Test Product",
    "description": "Test Description",
    "category": 5,
    "images_qty": 3
}


class TestPositiveCases:
    """Тесты положительных результатов предсказания"""
    
    def test_verified_seller_with_images(self):
        data = VALID_AD_DATA.copy()
        response = client.post("/predict", json=data)
        
        assert response.status_code == 200
        result = response.json()
        assert result["is_approved"] == True
        assert "Advertisement is approved" in result["message"]
    
    def test_verified_seller_without_images(self):
        data = VALID_AD_DATA.copy()
        data["images_qty"] = 0
        response = client.post("/predict", json=data)
        
        assert response.status_code == 200
        result = response.json()
        assert result["is_approved"] == True
    
    def test_unverified_seller_with_images(self):
        data = VALID_AD_DATA.copy()
        data["is_verified_seller"] = False
        response = client.post("/predict", json=data)
        
        assert response.status_code == 200
        result = response.json()
        assert result["is_approved"] == True
        assert "Advertisement is approved" in result["message"]


class TestNegativeCases:
    """Тесты отрицательных результатов предсказания"""
    
    def test_unverified_seller_without_images(self):
        data = VALID_AD_DATA.copy()
        data["is_verified_seller"] = False
        data["images_qty"] = 0
        response = client.post("/predict", json=data)
        
        assert response.status_code == 200
        result = response.json()
        assert result["is_approved"] == False
        assert "Advertisement is not approved" in result["message"]


class TestValidation:
    """Тесты валидации входных данных"""
    
    def test_missing_required_field(self):
        data = VALID_AD_DATA.copy()
        del data["seller_id"]
        
        response = client.post("/predict", json=data)
        assert response.status_code == 422
    
    def test_invalid_seller_id_type(self):
        data = VALID_AD_DATA.copy()
        data["seller_id"] = "not_a_number"
        
        response = client.post("/predict", json=data)
        assert response.status_code == 422
    
    def test_negative_seller_id(self):
        data = VALID_AD_DATA.copy()
        data["seller_id"] = -1
        
        response = client.post("/predict", json=data)
        assert response.status_code == 422
    
    def test_invalid_category_range(self):
        data = VALID_AD_DATA.copy()
        data["category"] = 10001
        
        response = client.post("/predict", json=data)
        assert response.status_code == 422
    
    def test_negative_images_qty(self):
        data = VALID_AD_DATA.copy()
        data["images_qty"] = -1
        
        response = client.post("/predict", json=data)
        assert response.status_code == 422
    
    def test_too_many_images(self):
        data = VALID_AD_DATA.copy()
        data["images_qty"] = 21
        
        response = client.post("/predict", json=data)
        assert response.status_code == 422
    
    def test_empty_name(self):
        data = VALID_AD_DATA.copy()
        data["name"] = ""
        
        response = client.post("/predict", json=data)
        assert response.status_code == 422
    
    def test_name_too_long(self):
        data = VALID_AD_DATA.copy()
        data["name"] = "a" * 10001
        
        response = client.post("/predict", json=data)
        assert response.status_code == 422
    
    def test_empty_description(self):
        data = VALID_AD_DATA.copy()
        data["description"] = ""
        
        response = client.post("/predict", json=data)
        assert response.status_code == 422


class TestEdgeCases:
    """Тесты граничных случаев"""
    
    def test_minimum_values(self):
        data = {
            "seller_id": 1,
            "is_verified_seller": False,
            "item_id": 1,
            "name": "a",
            "description": "b",
            "category": 0,
            "images_qty": 0
        }
        
        response = client.post("/predict", json=data)
        assert response.status_code == 200
    
    def test_maximum_values(self):
        data = {
            "seller_id": 999999,
            "is_verified_seller": True,
            "item_id": 999999,
            "name": "a" * 500,
            "description": "b" * 10000,
            "category": 1000,
            "images_qty": 20
        }
        
        response = client.post("/predict", json=data)
        assert response.status_code == 200


def test_business_logic_error_handling():
    response = client.post("/predict?value_error=true", json=VALID_AD_DATA)
    assert response.status_code == 500
    assert "Internal server error" in response.json()["detail"]
