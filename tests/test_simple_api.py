import sys
sys.path.append('.')
import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, AsyncMock
from main import app
from routers.predict import pred_service
from model import model_singleton
import warnings
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)


class TestPositiveCases:
    """Тесты положительных результатов предсказания"""
    
    @pytest.mark.parametrize(
                "seller_fixture, item_fixture", 
            [
                ("logged_seller", "created_item"),
                ("verified_seller", "created_item"),
                ("verified_seller", "created_item_zero_images"),
            ])
    def test_positive_scenarios(self, app_client, seller_fixture, item_fixture, request):
        seller = request.getfixturevalue(seller_fixture)
        item = request.getfixturevalue(item_fixture)
        logger.info(item)
        response = app_client.post(f'/simple_predict/{item["item_id"]}', json = {"item_id": item["item_id"]})
        assert response.status_code == 200
        assert response.json()['is_violation'] == False
        assert response.json()['probability'] < 0.5

class TestNegativeCases:
    """Тесты отрицательных результатов предсказания"""
    @pytest.mark.parametrize(
                "seller_fixture, item_fixture", 
            [
                ("logged_seller", "created_item_zero_images"),
            ])
    def test_unverified_seller_without_images(self, app_client, seller_fixture, item_fixture, request):
        seller = request.getfixturevalue(seller_fixture)
        item = request.getfixturevalue(item_fixture)
        response = app_client.post(f'/simple_predict/{item["item_id"]}', json = {"item_id": item["item_id"]})
        assert response.status_code == 200
        assert response.json()['is_violation'] == True
        assert response.json()['probability'] >= 0.5