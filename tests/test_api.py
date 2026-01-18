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
        """Верифицированный продавец с изображениями должен быть одобрен"""
        data = VALID_AD_DATA.copy()
        response = client.post("/predict", json=data)
        
        assert response.status_code == 200
        result = response.json()
        assert result["is_approved"] == True
        assert "Advertisment is approved" in result["message"]
    
    def test_verified_seller_without_images(self):
        """Верифицированный продавец без изображений должен быть одобрен"""
        data = VALID_AD_DATA.copy()
        data["images_qty"] = 0
        response = client.post("/predict", json=data)
        
        assert response.status_code == 200
        result = response.json()
        assert result["is_approved"] == True
    
    def test_unverified_seller_with_images(self):
        """Неверифицированный продавец с изображениями должен быть одобрен"""
        data = VALID_AD_DATA.copy()
        data["is_verified_seller"] = False
        response = client.post("/predict", json=data)
        
        assert response.status_code == 200
        result = response.json()
        assert result["is_approved"] == True
        assert "Advertisment is approved" in result["message"]


class TestNegativeCases:
    """Тесты отрицательных результатов предсказания"""
    
    def test_unverified_seller_without_images(self):
        """Неверифицированный продавец без изображений должен быть отклонен"""
        data = VALID_AD_DATA.copy()
        data["is_verified_seller"] = False
        data["images_qty"] = 0
        response = client.post("/predict", json=data)
        
        assert response.status_code == 200
        result = response.json()
        assert result["is_approved"] == False
        assert "Advertisment is not approved" in result["message"]


class TestValidation:
    """Тесты валидации входных данных"""
    
    def test_missing_required_field(self):
        """Отсутствие обязательного поля должно вызывать ошибку"""
        data = VALID_AD_DATA.copy()
        del data["seller_id"]
        
        response = client.post("/predict", json=data)
        assert response.status_code == 422
    
    def test_invalid_seller_id_type(self):
        """Неверный тип входного параметра должен вызывать ошибку"""
        data = VALID_AD_DATA.copy()
        data["seller_id"] = "not_a_number"
        
        response = client.post("/predict", json=data)
        assert response.status_code == 422
    
    def test_negative_seller_id(self):
        """Отрицательный seller_id должен вызывать ошибку"""
        data = VALID_AD_DATA.copy()
        data["seller_id"] = -1
        
        response = client.post("/predict", json=data)
        assert response.status_code == 422
    
    def test_invalid_category_range(self):
        """Категория вне диапазона должна вызывать ошибку"""
        data = VALID_AD_DATA.copy()
        data["category"] = 10001
        
        response = client.post("/predict", json=data)
        assert response.status_code == 422
    
    def test_negative_images_qty(self):
        """Отрицательное количество изображений должно вызывать ошибку"""
        data = VALID_AD_DATA.copy()
        data["images_qty"] = -1
        
        response = client.post("/predict", json=data)
        assert response.status_code == 422
    
    def test_too_many_images(self):
        """Слишком большое количество изображений должно вызывать ошибку"""
        data = VALID_AD_DATA.copy()
        data["images_qty"] = 21
        
        response = client.post("/predict", json=data)
        assert response.status_code == 422
    
    def test_empty_name(self):
        """Пустое название должно вызывать ошибку"""
        data = VALID_AD_DATA.copy()
        data["name"] = ""
        
        response = client.post("/predict", json=data)
        assert response.status_code == 422
    
    def test_name_too_long(self):
        """Слишком длинное название должно вызывать ошибку"""
        data = VALID_AD_DATA.copy()
        data["name"] = "a" * 10001
        
        response = client.post("/predict", json=data)
        assert response.status_code == 422
    
    def test_empty_description(self):
        """Пустое описание должно вызывать ошибку"""
        data = VALID_AD_DATA.copy()
        data["description"] = ""
        
        response = client.post("/predict", json=data)
        assert response.status_code == 422


class TestEdgeCases:
    """Тесты граничных случаев"""
    
    def test_minimum_values(self):
        """Минимальные допустимые значения"""
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
        """Максимальные допустимые значения"""
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


def test_business_logic_error_handling(monkeypatch):
    """Тест обработки ошибок в бизнес-логике"""
    
    response = client.post("/predict?value_error=true", json=VALID_AD_DATA)
    assert response.status_code == 500
    assert "Internal server error" in response.json()["detail"]
