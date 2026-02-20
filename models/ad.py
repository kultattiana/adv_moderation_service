from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime

class AdModel(BaseModel):
    item_id: int
    seller_id: int
    name: str
    description: str
    category: int
    images_qty: int
    is_closed: Optional[bool] = False
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None