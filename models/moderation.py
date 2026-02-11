from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime


class ModerationModel(BaseModel):
    id: int
    item_id: int
    status: str
    is_violation: Optional[bool] = None
    probability: Optional[float]= None
    error_message: Optional[str] = None
    created_at: Optional[datetime] = None
    processed_at: Optional[datetime] = None