from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime

class SellerModel(BaseModel):
    seller_id: int
    username: str
    email: str
    password: str
    is_verified: bool = False
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None