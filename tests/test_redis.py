import pytest
from unittest.mock import Mock, AsyncMock, patch, call
from datetime import datetime
from repositories.moderations import ModerationRepository, ModerationModel
from errors import ModerationNotFoundError
import asyncio

@pytest.mark.asyncio
class TestRedisUnit:

    async def test_get_latest_by_item_id_cache_hit(self, completed_moderation):
        """Тест: данные есть в Redis, возвращаем из кэша."""

        mock_moderation_storage = AsyncMock()
        mock_moderation_redis_storage = AsyncMock()
        
        moderation_repo = ModerationRepository(
            moderation_storage=mock_moderation_storage, 
            moderation_redis_storage=mock_moderation_redis_storage
        )
        
        mock_moderation_redis_storage.get_latest_by_item_id.return_value = completed_moderation
        
        result = await moderation_repo.get_latest_by_item_id(completed_moderation["item_id"])
        
        assert result is not None
        assert result.id == completed_moderation["id"]
        assert result.item_id == completed_moderation["item_id"]
        
        mock_moderation_redis_storage.get_latest_by_item_id.assert_called_once_with(
            completed_moderation["item_id"]
        )
        
        mock_moderation_storage.get_latest_by_item_id.assert_not_called()


    async def test_get_latest_by_item_id_cache_miss_db_hit(self, completed_moderation):
        """Тест: данных нет в Redis, но есть в БД - сохраняем в кэш."""
        
        mock_moderation_storage = AsyncMock()
        mock_moderation_redis_storage = AsyncMock()
        
        moderation_repo = ModerationRepository(
            moderation_storage=mock_moderation_storage, 
            moderation_redis_storage=mock_moderation_redis_storage
        )
        
        mock_moderation_redis_storage.get_latest_by_item_id.return_value = None
        mock_moderation_storage.select_latest_by_item_id.return_value = completed_moderation
        
        result = await moderation_repo.get_latest_by_item_id(completed_moderation["item_id"])
        
        assert result is not None
        assert result.id == completed_moderation["id"]
        assert result.item_id == completed_moderation["item_id"]
        
        mock_moderation_redis_storage.get_latest_by_item_id.assert_called_once_with(completed_moderation["item_id"])
        mock_moderation_storage.select_latest_by_item_id.assert_called_once_with(completed_moderation["item_id"])
        
        mock_moderation_redis_storage.set_latest_by_item_id.assert_called_once_with(completed_moderation["item_id"], completed_moderation)
        mock_moderation_redis_storage.set_by_task_id.assert_called_once_with(completed_moderation["id"], completed_moderation)

    
    async def test_get_latest_by_item_id_cache_miss_db_miss(self, completed_moderation):
        """Тест: данных нет ни в Redis, ни в БД - возвращаем None."""
        
        mock_moderation_storage = AsyncMock()
        mock_moderation_redis_storage = AsyncMock()
        
        moderation_repo = ModerationRepository(
            moderation_storage=mock_moderation_storage, 
            moderation_redis_storage=mock_moderation_redis_storage
        )

        mock_moderation_redis_storage.get_latest_by_item_id.return_value = None
        mock_moderation_storage.select_latest_by_item_id.return_value = None
        
        
        result = await moderation_repo.get_latest_by_item_id(completed_moderation["item_id"])

        assert result is None
        
        mock_moderation_redis_storage.get_latest_by_item_id.assert_called_once_with(completed_moderation["item_id"])
        mock_moderation_storage.select_latest_by_item_id.assert_called_once_with(completed_moderation["item_id"])
    


    async def test_get_by_task_id_cache_hit(self, completed_moderation):
        
        mock_moderation_storage = AsyncMock()
        mock_moderation_redis_storage = AsyncMock()
        
        moderation_repo = ModerationRepository(
            moderation_storage=mock_moderation_storage,
            moderation_redis_storage=mock_moderation_redis_storage
        )
        
        mock_moderation_redis_storage.get_by_task_id.return_value = completed_moderation
        
        result = await moderation_repo.get_by_task_id(completed_moderation["id"])
        
        assert result is not None
        assert result.id == completed_moderation["id"]
        assert result.item_id == completed_moderation["item_id"]
        assert result.status == "completed"

        mock_moderation_redis_storage.get_by_task_id.assert_called_once_with(completed_moderation["id"])
        mock_moderation_storage.select_by_task_id.assert_not_called()
        mock_moderation_redis_storage.set_by_task_id.assert_not_called()
        mock_moderation_redis_storage.set_latest_by_item_id.assert_not_called()

    
    async def test_get_by_task_id_cache_miss_db_hit_completed(self, completed_moderation):
    
        mock_moderation_storage = AsyncMock()
        mock_moderation_redis_storage = AsyncMock()
        
        moderation_repo = ModerationRepository(
            moderation_storage=mock_moderation_storage,
            moderation_redis_storage=mock_moderation_redis_storage
        )
        
        mock_moderation_redis_storage.get_by_task_id.return_value = None
        mock_moderation_storage.select_by_task_id.return_value = completed_moderation
        
        result = await moderation_repo.get_by_task_id(completed_moderation["id"])
        
        assert result is not None
        assert result.id == completed_moderation["id"]
        assert result.item_id == completed_moderation["item_id"]
        
        mock_moderation_redis_storage.get_by_task_id.assert_called_once_with(completed_moderation["id"])
        mock_moderation_storage.select_by_task_id.assert_called_once_with(completed_moderation["id"])
        
        mock_moderation_redis_storage.set_by_task_id.assert_called_once_with(
            completed_moderation["id"], 
            completed_moderation
        )
        mock_moderation_redis_storage.set_latest_by_item_id.assert_called_once_with(
            completed_moderation["item_id"], 
            completed_moderation
        )
    

    async def test_get_by_task_id_cache_miss_db_hit_pending(self, pending_moderation):
        
        mock_moderation_storage = AsyncMock()
        mock_moderation_redis_storage = AsyncMock()
        
        moderation_repo = ModerationRepository(
            moderation_storage=mock_moderation_storage,
            moderation_redis_storage=mock_moderation_redis_storage
        )
        
        mock_moderation_redis_storage.get_by_task_id.return_value = None
        mock_moderation_storage.select_by_task_id.return_value = pending_moderation
        
        result = await moderation_repo.get_by_task_id(pending_moderation["id"])
        
        assert result is not None
        assert result.id == pending_moderation["id"]
        assert result.item_id == pending_moderation["item_id"]
        assert result.status == "pending"
        
        mock_moderation_redis_storage.get_by_task_id.assert_called_once_with(pending_moderation["id"])
        mock_moderation_storage.select_by_task_id.assert_called_once_with(pending_moderation["id"])
        
        mock_moderation_redis_storage.set_by_task_id.assert_not_called()
        mock_moderation_redis_storage.set_latest_by_item_id.assert_not_called()

    
    async def test_update_pending_status(self, pending_moderation):
        
        mock_moderation_storage = AsyncMock()
        mock_moderation_redis_storage = AsyncMock()
        
        moderation_repo = ModerationRepository(
            moderation_storage=mock_moderation_storage,
            moderation_redis_storage=mock_moderation_redis_storage
        )
        
        updated_moderation = pending_moderation.copy()
        updated_moderation["status"] = "completed"
        
        mock_moderation_storage.update.return_value = updated_moderation
        
        result = await moderation_repo.update(
            pending_moderation["id"], 
            status="completed"
        )
        
        assert result is not None
        assert result.status == "completed"
        
        mock_moderation_storage.update.assert_called_once_with(
            pending_moderation["id"], 
            status="completed"
        )
        
        mock_moderation_redis_storage.set_by_task_id.assert_called_once()
        mock_moderation_redis_storage.set_latest_by_item_id.assert_called_once()

    
    async def test_delete_latest(self, completed_moderation):
        
        mock_moderation_storage = AsyncMock()
        mock_moderation_redis_storage = AsyncMock()
        
        moderation_repo = ModerationRepository(
            moderation_storage=mock_moderation_storage,
            moderation_redis_storage=mock_moderation_redis_storage
        )
        
        mock_moderation_redis_storage.get_by_task_id.return_value = completed_moderation
        mock_moderation_storage.delete.return_value = completed_moderation
        mock_moderation_redis_storage.get_latest_by_item_id.return_value = completed_moderation
        
        mock_moderation_storage.select_latest_by_item_id.return_value = None
        
        result = await moderation_repo.delete(completed_moderation["id"])
        
        assert result is not None
        assert result.id == completed_moderation["id"]
        
        mock_moderation_redis_storage.get_by_task_id.assert_called_once_with(completed_moderation["id"])
        mock_moderation_storage.delete.assert_called_once_with(completed_moderation["id"])
        mock_moderation_redis_storage.delete_by_task_id.assert_called_once_with(completed_moderation["id"])
        
        mock_moderation_redis_storage.delete_latest_by_item_id.assert_called_once_with(completed_moderation["item_id"])
        
        mock_moderation_redis_storage.set_latest_by_item_id.assert_not_called()
        mock_moderation_redis_storage.set_by_task_id.assert_not_called()
    
    
    async def test_delete_all_by_item_id(self, completed_moderation):
        
        mock_moderation_storage = AsyncMock()
        mock_moderation_redis_storage = AsyncMock()
        
        moderation_repo = ModerationRepository(
            moderation_storage=mock_moderation_storage,
            moderation_redis_storage=mock_moderation_redis_storage
        )

        mock_moderation_redis_storage.get_latest_by_item_id.return_value = completed_moderation
            
        await moderation_repo.delete_all_by_item_id(completed_moderation["item_id"])
        
        mock_moderation_storage.delete_by_item_id.assert_called_once_with(completed_moderation["item_id"])
        mock_moderation_redis_storage.delete_by_task_id.assert_called_once_with(completed_moderation["id"])
        mock_moderation_redis_storage.delete_latest_by_item_id.assert_called_once_with(completed_moderation["item_id"])
    

    async def test_invalidate_by_item_id(self, completed_moderation):

        mock_moderation_storage = AsyncMock()
        mock_moderation_redis_storage = AsyncMock()
        
        moderation_repo = ModerationRepository(
            moderation_storage=mock_moderation_storage,
            moderation_redis_storage=mock_moderation_redis_storage
        )

        mock_moderation_redis_storage.get_latest_by_item_id.return_value = completed_moderation
        
        await moderation_repo.invalidate_by_item_id(completed_moderation["item_id"])

        mock_moderation_redis_storage.delete_by_task_id.assert_called_once_with(completed_moderation["id"])
        mock_moderation_redis_storage.delete_latest_by_item_id.assert_called_once_with(completed_moderation["item_id"])
    
    
    async def test_invalidate_by_seller_id_with_items(self, completed_moderation):
        mock_moderation_storage = AsyncMock()
        mock_moderation_redis_storage = AsyncMock()
        
        moderation_repo = ModerationRepository(
            moderation_storage=mock_moderation_storage,
            moderation_redis_storage=mock_moderation_redis_storage
        )
        
        seller_id = 123
        item_ids = [1, 2, 3]
        
        mock_moderation_storage.select_item_ids_by_seller_id.return_value = item_ids
        mock_moderation_redis_storage.get_latest_by_item_id.return_value = completed_moderation

        await moderation_repo.invalidate_by_seller_id(seller_id)
            
        mock_moderation_storage.select_item_ids_by_seller_id.assert_called_once_with(seller_id)
        assert mock_moderation_redis_storage.get_latest_by_item_id.call_count == 3


@pytest.mark.asyncio
@pytest.mark.integration
class TestModerationRepositoryIntegration:

    async def test_create_and_get_latest_by_item_id_integration(
        self, 
        created_item
    ):
        repo = ModerationRepository()
        item_id = created_item["item_id"]
    
        mod1 = await repo.create(
            item_id=item_id,
            status="pending",
            is_violation=False,
            probability=0.0,
            error_message=None
        )
        
        assert mod1.id is not None
        assert mod1.item_id == item_id
        assert mod1.status == "pending"
        
        await asyncio.sleep(0.1)
        
        mod2 = await repo.update(
            id=mod1.id,
            status="completed",
            probability = 0.95
        )
        
        latest = await repo.get_latest_by_item_id(item_id)
        
        assert latest is not None
        assert latest.id == mod2.id
        assert latest.status == "completed"
        assert latest.probability == 0.95
        
        cached = await repo.moderation_redis_storage.get_latest_by_item_id(item_id)
        assert cached is not None
        assert cached["id"] == mod2.id
        
        cached_task = await repo.moderation_redis_storage.get_by_task_id(mod2.id)
        assert cached_task is not None
        assert cached_task["id"] == mod2.id

    async def test_get_latest_by_item_id_cache_hit_integration(
        self,
        created_item
    ):
        
        repo = ModerationRepository()
        item_id = created_item["item_id"]
        
        mod = await repo.create(
            item_id=item_id,
            status="completed",
            is_violation=False,
            probability=0.5,
            error_message=None
        )
        
        await repo.get_latest_by_item_id(item_id)
        
        await repo.moderation_storage.delete(mod.id)
        
        result2 = await repo.get_latest_by_item_id(item_id)
        
        assert result2 is not None
        assert result2.id == mod.id
        
        await repo.moderation_redis_storage.delete_latest_by_item_id(item_id)
        result3 = await repo.get_latest_by_item_id(item_id)
        assert result3 is None

    async def test_get_latest_by_item_id_cache_miss_db_hit_integration(
        self,
        created_item
    ):
       
        repo = ModerationRepository()
        item_id = created_item["item_id"]
        
        mod = await repo.create(
            item_id=item_id,
            status="completed",
            is_violation=False,
            probability=0.5,
            error_message=None
        )
        
        await repo.moderation_redis_storage.delete_latest_by_item_id(item_id)
        await repo.moderation_redis_storage.delete_by_task_id(mod.id)
        
        cached_before = await repo.moderation_redis_storage.get_latest_by_item_id(item_id)
        assert cached_before is None
    
        result = await repo.get_latest_by_item_id(item_id)
        
        assert result.id == mod.id
    
        cached_after = await repo.moderation_redis_storage.get_latest_by_item_id(item_id)
        assert cached_after is not None
        assert cached_after["id"] == mod.id
        
        cached_task = await repo.moderation_redis_storage.get_by_task_id(mod.id)
        assert cached_task is not None
        assert cached_task["id"] == mod.id

    async def test_get_latest_by_item_id_cache_miss_db_miss_integration(
        self
    ):
        
        repo = ModerationRepository()
        non_existent_item_id = 999999
        
        result = await repo.get_latest_by_item_id(non_existent_item_id)
        
        assert result is None
        
        cached = await repo.moderation_redis_storage.get_latest_by_item_id(non_existent_item_id)
        assert cached is None

    async def test_get_by_task_id_cache_hit_integration(
        self,
        created_item
    ):
        
        repo = ModerationRepository()
        item_id = created_item["item_id"]
        
        mod = await repo.create(
            item_id=item_id,
            status="completed",
            is_violation=False,
            probability=0.5,
            error_message=None
        )
        
        
        await repo.get_by_task_id(mod.id)
        
        await repo.moderation_storage.delete(mod.id)
        
        result2 = await repo.get_by_task_id(mod.id)
        
        assert result2 is not None
        assert result2.id == mod.id
        
        await repo.moderation_redis_storage.delete_by_task_id(mod.id)
        
        with pytest.raises(ModerationNotFoundError):
            await repo.get_by_task_id(mod.id)

    async def test_get_by_task_id_cache_miss_db_hit_completed_integration(
        self,
        created_item
    ):
        repo = ModerationRepository()
        item_id = created_item["item_id"]
        
        mod = await repo.create(
            item_id=item_id,
            status="completed",
            is_violation=False,
            probability=0.5,
            error_message=None
        )
        
        await repo.moderation_redis_storage.delete_by_task_id(mod.id)
        await repo.moderation_redis_storage.delete_latest_by_item_id(item_id)
        
        result = await repo.get_by_task_id(mod.id)
        
        assert result.id == mod.id
        
        cached_task = await repo.moderation_redis_storage.get_by_task_id(mod.id)
        assert cached_task is not None
        assert cached_task["id"] == mod.id
        
        cached_latest = await repo.moderation_redis_storage.get_latest_by_item_id(item_id)
        assert cached_latest is not None
        assert cached_latest["id"] == mod.id

    async def test_get_by_task_id_cache_miss_db_hit_pending_integration(
        self,
        created_item
    ):
        repo = ModerationRepository()
        item_id = created_item["item_id"]
        
        mod = await repo.create(
            item_id=item_id,
            status="pending",
            is_violation=False,
            probability=0.0,
            error_message=None
        )
        
        await repo.moderation_redis_storage.delete_by_task_id(mod.id)
        await repo.moderation_redis_storage.delete_latest_by_item_id(item_id)
        
        result = await repo.get_by_task_id(mod.id)
        
        assert result.id == mod.id
        assert result.status == "pending"
        
        cached_task = await repo.moderation_redis_storage.get_by_task_id(mod.id)
        assert cached_task is None
        
        cached_latest = await repo.moderation_redis_storage.get_latest_by_item_id(item_id)
        assert cached_latest is None

    async def test_get_by_task_id_db_miss_integration(self):
        repo = ModerationRepository()
        non_existent_task_id = 999999
        
        with pytest.raises(ModerationNotFoundError):
            await repo.get_by_task_id(non_existent_task_id)

    async def test_update_pending_to_completed_integration(
        self,
        created_item,
    ):
        repo = ModerationRepository()
        item_id = created_item["item_id"]
        
        mod = await repo.create(
            item_id=item_id,
            status="pending",
            is_violation=False,
            probability=0.0,
            error_message=None
        )
        
        cached_before = await repo.moderation_redis_storage.get_by_task_id(mod.id)
        assert cached_before is None
        
        updated = await repo.update(
            mod.id,
            status="completed",
            is_violation=True,
            probability=0.99
        )
        
        assert updated.status == "completed"
        assert updated.probability == 0.99
        
        cached_task = await repo.moderation_redis_storage.get_by_task_id(mod.id)
        assert cached_task is not None
        assert cached_task["status"] == "completed"
        
        cached_latest = await repo.moderation_redis_storage.get_latest_by_item_id(item_id)
        assert cached_latest is not None
        assert cached_latest["id"] == mod.id

    async def test_delete_latest_integration(
        self,
        created_item
    ):
        repo = ModerationRepository()
        item_id = created_item["item_id"]
        
        mod = await repo.create(
            item_id=item_id,
            status="pending",
            is_violation=None,
            probability=None,
            error_message=None
        )

        await repo.update(
            id=mod.id,
            status="completed",
            is_violation = True,
            probability = 0.95
        )
        
        cached_before = await repo.moderation_redis_storage.get_latest_by_item_id(item_id)
        assert cached_before is not None
        assert cached_before["id"] == mod.id
        
        deleted = await repo.delete(mod.id)
        
        assert deleted.id == mod.id
        
        cached_after = await repo.moderation_redis_storage.get_latest_by_item_id(item_id)
        assert cached_after is None
        
        cached_task = await repo.moderation_redis_storage.get_by_task_id(mod.id)
        assert cached_task is None
        
        with pytest.raises(ModerationNotFoundError):
            await repo.get_by_task_id(mod.id)


    async def test_delete_all_by_item_id(
        self,
        created_item
    ):
        repo = ModerationRepository()
        item_id = created_item["item_id"]

        mod = await repo.create(
                item_id=item_id,
                status="pending",
                is_violation=None,
                probability=None,
                error_message=None
            )
        
        mods = []
        for i in range(3):
            mod_ = await repo.update(
                id=mod.id,
                item_id=item_id,
                status="completed",
                is_violation=False,
                probability=0.1 * i,
                error_message=None
            )
            mods.append(mod_)
            await asyncio.sleep(0.1)
        
        for mod in mods:
            cached = await repo.moderation_redis_storage.get_by_task_id(mod.id)
            assert cached is not None
        
        cached_latest = await repo.moderation_redis_storage.get_latest_by_item_id(item_id)
        assert cached_latest is not None
        assert cached_latest["id"] == mods[-1].id
        
        await repo.delete_all_by_item_id(item_id)
        
        for mod in mods:
            cached = await repo.moderation_redis_storage.get_by_task_id(mod.id)
            assert cached is None
        
        cached_latest = await repo.moderation_redis_storage.get_latest_by_item_id(item_id)
        assert cached_latest is None
        
        result = await repo.get_latest_by_item_id(item_id)
        assert result is None


    async def test_invalidate_by_item_id_with_latest_integration(
        self,
        created_item
    ):
        repo = ModerationRepository()
        item_id = created_item["item_id"]
        
        mod = await repo.create(
            item_id=item_id,
            status="pending",
            is_violation=None,
            probability=None,
            error_message=None
        )

        await repo.update(
                id=mod.id,
                item_id=item_id,
                status="completed",
                is_violation=False,
                probability=0.002,
                error_message=None
            )
        
        cached_latest = await repo.moderation_redis_storage.get_latest_by_item_id(item_id)
        assert cached_latest is not None
        
        cached_task = await repo.moderation_redis_storage.get_by_task_id(mod.id)
        assert cached_task is not None
        
        await repo.invalidate_by_item_id(item_id)
        
        cached_latest_after = await repo.moderation_redis_storage.get_latest_by_item_id(item_id)
        assert cached_latest_after is None
        
        cached_task_after = await repo.moderation_redis_storage.get_by_task_id(mod.id)
        assert cached_task_after is None
        
        result = await repo.get_latest_by_item_id(item_id)
        assert result is None



    async def test_invalidate_by_seller_id_with_items_integration(
        self,
        created_seller,
        created_item
    ):
        repo = ModerationRepository()
        seller_id = created_seller["seller_id"]
        item_id = created_item["item_id"]
        
        mod = await repo.create(
            item_id=item_id,
            status="pending",
            is_violation=None,
            probability=None,
            error_message=None
        )

        await repo.update(
                id=mod.id,
                item_id=item_id,
                status="completed",
                is_violation=False,
                probability=0.002,
                error_message=None
            )
        
        cached_latest = await repo.moderation_redis_storage.get_latest_by_item_id(item_id)
        assert cached_latest is not None
        
        await repo.invalidate_by_seller_id(seller_id)
        
        cached_latest_after = await repo.moderation_redis_storage.get_latest_by_item_id(item_id)
        assert cached_latest_after is None
        
        result = await repo.get_latest_by_item_id(item_id)
        assert result is None
