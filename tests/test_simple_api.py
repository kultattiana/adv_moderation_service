import sys
sys.path.append('.')
import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, AsyncMock
from main import app
#from routers.predict import pred_service
from model import model_singleton
from repositories.ads import AdRepository
from repositories.sellers import SellerRepository
from services.advertisements import AdvertisementService
from services.moderations import ModerationService
from models.moderation import ModerationModel
import warnings
import logging
from dependencies import mod_service, ad_service

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)

@pytest.mark.integration
class TestPositiveCases:
    """Тесты положительных результатов предсказания"""
    
    @pytest.mark.parametrize(
                "seller_fixture, item_fixture", 
            [
                ("created_seller", "created_item"),
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

@pytest.mark.integration
class TestNegativeCases:
    """Тесты отрицательных результатов предсказания"""
    @pytest.mark.parametrize(
                "seller_fixture, item_fixture", 
            [
                ("created_seller", "created_item_zero_images"),
            ])
    def test_unverified_seller_without_images(self, app_client, seller_fixture, item_fixture, request):
        seller = request.getfixturevalue(seller_fixture)
        item = request.getfixturevalue(item_fixture)
        response = app_client.post(f'/simple_predict/{item["item_id"]}', json = {"item_id": item["item_id"]})
        assert response.status_code == 200
        assert response.json()['is_violation'] == True
        assert response.json()['probability'] >= 0.5


class TestSimplePredictAPIUnit:

    @pytest.mark.parametrize(
        "seller_fixture, item_fixture", 
        [
            ("created_seller_data", "created_item_data"),
            ("verified_seller_data", "created_item_data"),
            ("verified_seller_data", "created_item_zero_images_data"),
        ]
    )
    def test_positive_scenarios_unit(self, app_client_with_mocks, seller_fixture, 
                                     item_fixture, request, mock_ad_storage, mock_seller_storage, 
                                     pending_moderation, completed_moderation, override_auth_unit):
        seller = request.getfixturevalue(seller_fixture)
        item = request.getfixturevalue(item_fixture)
        
        mock_moderation_repo = AsyncMock()
        mock_mod_service = ModerationService(moderation_repo=mock_moderation_repo)
        mock_moderation_repo.get_latest_by_item_id.return_value = None
        mock_moderation_repo.create.return_value = ModerationModel(**pending_moderation)
        mock_moderation_repo.update.return_value = ModerationModel(**completed_moderation)

        predict_request = { "seller_id": seller["seller_id"],
                            "is_verified_seller": seller["is_verified"],
                            "item_id": item["item_id"],
                            "name": item["name"],
                            "description": item["description"],
                            "category": item["category"],
                            "images_qty": item["images_qty"]
                        }
        mock_ad_storage.select_for_prediction.return_value = predict_request

        mock_ad_repo = AdRepository(ad_storage=mock_ad_storage)
        mock_seller_repo = SellerRepository(seller_storage=mock_seller_storage)
        
        mock_ad_service = AdvertisementService(ad_repo=mock_ad_repo, seller_repo=mock_seller_repo, moderation_repo=mock_moderation_repo)
        
        app_client_with_mocks.app.dependency_overrides[mod_service] = lambda: mock_mod_service
        app_client_with_mocks.app.dependency_overrides[ad_service] = lambda: mock_ad_service
        with patch('services.predictions.PredictionService.mod_service', mock_mod_service), \
            patch('services.predictions.PredictionService.ad_repo', mock_ad_repo):
        
            response = app_client_with_mocks.post(f'/simple_predict/{item["item_id"]}', 
                                            json={"item_id": item["item_id"]})
            
            assert response.status_code == 200
            assert response.json()['is_violation'] == False
            assert response.json()['probability'] < 0.5
            mock_moderation_repo.get_latest_by_item_id.assert_called_once()
            mock_moderation_repo.create.assert_called_once()
            mock_moderation_repo.update.assert_called_once()
            mock_ad_storage.select_for_prediction.assert_called_once()
    
    @pytest.mark.parametrize(
        "seller_fixture, item_fixture", 
        [("created_seller_data", "created_item_zero_images_data")]
    )
    def test_unverified_seller_without_images_unit(self, app_client_with_mocks, 
                                                  seller_fixture, item_fixture, 
                                                  request, mock_ad_storage, mock_seller_storage,
                                                  pending_moderation, completed_moderation, override_auth_unit):
        seller = request.getfixturevalue(seller_fixture)
        item = request.getfixturevalue(item_fixture)

        mock_mod_service = AsyncMock()
        mock_mod_service.get_latest_by_item_id.return_value = None
        mock_mod_service.register.return_value = ModerationModel(**pending_moderation)
        mock_mod_service.update.return_value = ModerationModel(**completed_moderation)
        mock_moderation_repo = AsyncMock()

        predict_request = { "seller_id": seller["seller_id"],
                            "is_verified_seller": seller["is_verified"],
                            "item_id": item["item_id"],
                            "name": item["name"],
                            "description": item["description"],
                            "category": item["category"],
                            "images_qty": item["images_qty"]
                        }

        mock_ad_repo = AdRepository(ad_storage=mock_ad_storage)
        mock_seller_repo = SellerRepository(seller_storage=mock_seller_storage)
        
        mock_ad_service = AdvertisementService(ad_repo=mock_ad_repo, seller_repo=mock_seller_repo, moderation_repo=mock_moderation_repo)
        
        app_client_with_mocks.app.dependency_overrides[mod_service] = lambda: mock_mod_service
        app_client_with_mocks.app.dependency_overrides[ad_service] = lambda: mock_ad_service
        with patch('services.predictions.PredictionService.mod_service', mock_mod_service), \
            patch('services.predictions.PredictionService.ad_repo', mock_ad_repo):
            mock_ad_storage.select_for_prediction.return_value = predict_request
            
            response = app_client_with_mocks.post(f'/simple_predict/{item["item_id"]}', 
                                            json={"item_id": item["item_id"]})
            
            assert response.status_code == 200
            assert response.json()['is_violation'] == True
            assert response.json()['probability'] >= 0.5
            mock_mod_service.get_latest_by_item_id.assert_called_once()
            mock_mod_service.register.assert_called_once()
            mock_mod_service.update.assert_called_once()
            mock_ad_storage.select_for_prediction.assert_called_once()