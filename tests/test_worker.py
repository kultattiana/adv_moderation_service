import asyncio
from unittest.mock import AsyncMock
from errors import AdNotFoundError
import asyncio
from datetime import datetime, timezone
import pytest
from workers.moderation_worker import KafkaConsumerWorker


@pytest.mark.integration
class TestKafkaConsumerWorkerIntegration:
    
    def test_process_message_integration_sync(self, worker, sample_message):
                                              
        async def run_test():
            test_worker = KafkaConsumerWorker()
            
            
            await test_worker.initialize()
            
            try:
                result = await test_worker.process_message(sample_message)
                return result
            finally:
                await test_worker.cleanup()
        
        result = asyncio.run(run_test())
        
        assert result is True

class TestKafkaConsumerWorkerUnit:
    
    def test_process_message_success(self, worker, sample_message_data):
        worker.ml_service.simple_predict.return_value = (False, 0.12)
        worker.mod_service.update_status = AsyncMock()
        
        result = asyncio.run(worker.process_message(sample_message_data))
        
        assert result is True
        
        worker.ml_service.simple_predict.assert_called_once_with(sample_message_data["item_id"], sample_message_data["task_id"])
        
       
    def test_process_message_ad_not_found(self, worker, sample_message_data):
        worker.ml_service.simple_predict.side_effect = AdNotFoundError()
        worker.send_to_dlq = AsyncMock()
        
        result = asyncio.run(worker.process_message(sample_message_data))
        
        assert result is False
        
        worker.mod_service.update_status.assert_called_once()
        call_args = worker.mod_service.update_status.call_args[0]
        assert call_args[1]["status"] == "failed"
        assert "not found" in call_args[1]["error_message"]
        
        worker.send_to_dlq.assert_called_once()
    
    
    def test_send_to_dlq(self, worker, sample_message_data):
        error_message = "Test error"
        retry_count = 2
    
        asyncio.run(worker.send_to_dlq(error_message, sample_message_data, retry_count))
        
        worker.dlq_producer.send_and_wait.assert_called_once()
        call_args = worker.dlq_producer.send_and_wait.call_args[0]
        
        assert call_args[0] == "moderation_dlq"
        
        dlq_message = call_args[1]
        assert dlq_message["original"] == sample_message_data
        assert dlq_message["error"] == error_message
        assert dlq_message["retry_count"] == retry_count
        assert "timestamp" in dlq_message
    

    
    def test_cleanup(self, worker):
        worker.consumer.stop = AsyncMock()
        worker.dlq_producer.stop = AsyncMock()
        
        asyncio.run(worker.cleanup())
        
        worker.consumer.stop.assert_called_once()
        worker.dlq_producer.stop.assert_called_once()