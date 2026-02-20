from dataclasses import dataclass
from models.moderation import ModerationModel
from typing import Mapping
from typing import Sequence
from typing import Any
from repositories.moderations import ModerationRepository
from errors import AdNotFoundError
import asyncpg

@dataclass(frozen=True)
class ModerationService:

    moderation_repo: ModerationRepository = ModerationRepository()

    async def register(self, values: Mapping[str, Any]) -> ModerationModel:
        try:
            return await self.moderation_repo.create(**values)
        except asyncpg.exceptions.ForeignKeyViolationError:
            raise AdNotFoundError
    
    async def ensure_idempotency(self, values: Mapping[str, Any]) -> ModerationModel:
        return await self.moderation_repo.ensure_idempotency(**values)
    
    async def get_many(self) -> Sequence[ModerationModel]:
        return await self.moderation_repo.get_many()
    
    async def get_by_task_id(self, id: int) -> ModerationModel:
        return await self.moderation_repo.get_by_task_id(id)

    async def get_latest_by_item_id(self, item_id: int) -> ModerationModel:
        return await self.moderation_repo.get_latest_by_item_id(item_id)
    
    async def delete(self, task_id: int) -> ModerationModel:
        return await self.moderation_repo.delete(task_id)

    async def update_status(self, task_id, updates: Mapping[str, Any]) -> ModerationModel:
        return await self.moderation_repo.update(task_id, **updates)
