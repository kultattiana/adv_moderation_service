import pytest
from unittest.mock import AsyncMock, patch
from http import HTTPStatus
from errors import ModelNotLoadedError, ModerationNotFoundError
from repositories.moderations import ModerationRepository
from datetime import datetime
from models.moderation import ModerationModel
from services.moderations import ModerationService

@pytest.mark.integration
class TestModerationAPI:

    def test_async_predict_success_integration(self, app_client, created_item):
        response = app_client.get(f'/ads/{created_item["item_id"]}')
        assert response.status_code == HTTPStatus.OK
        item_id = created_item["item_id"]
        
        response = app_client.post(
            f"/async_predict/{item_id}",
            json={"item_id": item_id}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "task_id" in data
        assert data["status"] == "pending"
    

    def test_moderation_result_found(self, app_client, created_task_pending):
        
        task_id = created_task_pending["task_id"]
        response = app_client.get(f"/moderation_results/{task_id}")
    
        assert response.status_code == 200
        data = response.json()
        assert data["task_id"] == task_id
        assert data["status"] == "pending"
        assert data["is_violation"] is None
        assert data["probability"] is None
    
    def test_moderation_result_not_found(self, app_client):
        
        task_id = "non-existent-id"
        response = app_client.get(f"/moderation_result/{task_id}")
        
        assert response.status_code == 404

class TestModerationAPIUnit:
    
    def test_async_predict_success_unit(self, app_client_with_mocks, created_moderation,
                                       created_item_data):
        mock_producer = AsyncMock()
        mock_producer.send_moderation_request.return_value = True


        mock_moderation_storage = AsyncMock()
        mock_moderation_redis_storage = AsyncMock()
        mock_moderation_repo = ModerationRepository(moderation_storage=mock_moderation_storage, 
                                                    moderation_redis_storage=mock_moderation_redis_storage)

        
        mock_moderation_service = ModerationService(moderation_repo=mock_moderation_repo)
        
        mock_moderation_redis_storage.get_latest_by_item_id.return_value = None
        mock_moderation_storage.create.return_value = created_moderation

        
        with patch('routers.async_predict.kafka_producer', mock_producer), \
             patch('routers.async_predict.mod_service', mock_moderation_service):
            
            response = app_client_with_mocks.post(
                f"/async_predict/{created_item_data['item_id']}",
                json={"item_id": created_item_data['item_id']}
            )
            
            assert response.status_code == 200
            data = response.json()
            assert "task_id" in data
            assert data["status"] == "pending"
            
            mock_producer.send_moderation_request.assert_called_once()
            mock_moderation_storage.create.assert_called_once()
            mock_moderation_redis_storage.get_latest_by_item_id.assert_called_once()

    
    def test_async_predict_kafka_error_unit(self, app_client_with_mocks, created_item_data, created_moderation):
        mock_producer = AsyncMock()
        mock_producer.send_moderation_request = AsyncMock(side_effect=ModelNotLoadedError)
        
        mock_moderation_storage = AsyncMock()
        mock_moderation_redis_storage = AsyncMock()
        mock_moderation_repo = ModerationRepository(moderation_storage=mock_moderation_storage, 
                                                    moderation_redis_storage=mock_moderation_redis_storage)

        
        mock_moderation_service = ModerationService(moderation_repo=mock_moderation_repo)
        
        mock_moderation_redis_storage.get_latest_by_item_id.return_value = None
        mock_moderation_storage.create.return_value = created_moderation

        
        with patch('routers.async_predict.kafka_producer', mock_producer), \
             patch('routers.async_predict.mod_service', mock_moderation_service):
            
            response = app_client_with_mocks.post(
                f"/async_predict/{created_item_data['item_id']}",
                json={"item_id": created_item_data['item_id']}
            )
            
            assert response.status_code == 503
            data = response.json()
            assert "Model" in data["detail"]
    
    def test_moderation_result_found_unit(self, app_client_with_mocks, completed_moderation):
        
        mock_moderation_storage = AsyncMock()
        mock_moderation_redis_storage = AsyncMock()
        mock_moderation_repo = ModerationRepository(moderation_storage=mock_moderation_storage, 
                                                    moderation_redis_storage=mock_moderation_redis_storage)

        
        mock_moderation_service = ModerationService(moderation_repo=mock_moderation_repo)
        
        mock_moderation_redis_storage.get_by_task_id.return_value = None
        mock_moderation_storage.select_by_task_id.return_value = completed_moderation

        with patch('routers.moderation_results.mod_service', mock_moderation_service):
            
            task_id = completed_moderation["id"]
            response = app_client_with_mocks.get(f"/moderation_results/{task_id}")
        
            assert response.status_code == 200
            data = response.json()
            assert data["task_id"] == task_id
            assert data["status"] == "completed"

            mock_moderation_redis_storage.set_latest_by_item_id.assert_called_once()
            mock_moderation_redis_storage.set_by_task_id.assert_called_once()
            mock_moderation_redis_storage.get_by_task_id.assert_called_once()
            mock_moderation_storage.select_by_task_id.assert_called_once()

    
    def test_moderation_result_not_found_unit(self, app_client_with_mocks, completed_moderation):
        mock_moderation_storage = AsyncMock()
        mock_moderation_redis_storage = AsyncMock()
        mock_moderation_repo = ModerationRepository(moderation_storage=mock_moderation_storage, 
                                                    moderation_redis_storage=mock_moderation_redis_storage)

        
        mock_moderation_service = ModerationService(moderation_repo=mock_moderation_repo)
        
        mock_moderation_redis_storage.get_by_task_id.return_value = None
        mock_moderation_storage.select_by_task_id.side_effect = ModerationNotFoundError()

        with patch('routers.moderation_results.mod_service', mock_moderation_service):
            
            task_id = completed_moderation["id"]
            response = app_client_with_mocks.get(f"/moderation_results/{task_id}")
        
            assert response.status_code == 404

            mock_moderation_redis_storage.get_by_task_id.assert_called_once()
            mock_moderation_storage.select_by_task_id.assert_called_once()