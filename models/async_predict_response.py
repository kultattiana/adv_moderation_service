from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime
from enum import Enum

class ModerationStatusEnum(str, Enum):
    PENDING = "pending"
    COMPLETED = "completed"
    FAILED = "failed"

class AsyncPredictResponse(BaseModel):
    task_id: int = Field(..., description="ID задачи модерации")
    status: ModerationStatusEnum = Field(..., description="Статус модерации")
    message: str = Field(..., description="Сообщение о результате")