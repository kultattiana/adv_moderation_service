from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime


class ErrorModerationResultResponse(BaseModel):
    task_id: int
    status: str
    is_violation: Optional[bool] = None
    probability: Optional[float] = None
    error_message: Optional[str] = None

class ModerationResultResponse(BaseModel):
    task_id: int
    status: str
    is_violation: Optional[bool] = None
    probability: Optional[float] = None
