import pytest
from unittest.mock import AsyncMock, patch
from http import HTTPStatus
from errors import ModelNotLoadedError


class TestModerationAPI:

    def test_async_predict_success(self, app_client, created_item):
        mock_producer = AsyncMock()
        mock_producer.send_moderation_request = AsyncMock()
        mock_producer.send_moderation_request.return_value = True
        
        with patch('routers.async_predict.kafka_producer', mock_producer):
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
            
            mock_producer.send_moderation_request.assert_called_once()
    
    def test_async_predict_kafka_error(self, app_client, created_item):
        mock_producer = AsyncMock()
        mock_producer.send_moderation_request = AsyncMock(side_effect=ModelNotLoadedError)
        
        with patch('routers.async_predict.kafka_producer', mock_producer):
            response = app_client.get(f'/ads/{created_item["item_id"]}')
            assert response.status_code == HTTPStatus.OK
            item_id = created_item["item_id"]
            
            response = app_client.post(
                f"/async_predict/{item_id}",
                json={"item_id": item_id}
            )
            
            assert response.status_code == 503
            data = response.json()
            assert "Model" in data["detail"]
    

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