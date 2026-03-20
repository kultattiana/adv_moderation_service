from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime

class AccountModel(BaseModel):
    id: int
    seller_id: int
    login: str
    password: str
    salt: Optional[str] = None
    is_blocked: bool = False
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None