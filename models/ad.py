from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime

class AdModel(BaseModel):
    item_id: int
    seller_id: int
    name: str = Field(..., min_length = 1, max_length = 500, description = 'Название товара')
    description: str = Field(..., min_length = 1, max_length = 1000, description = 'Описание товара')
    category: int = Field(..., ge = 0, le = 100, description = 'Категория товара (от 0 до 100)')
    images_qty: int = Field(..., ge=0, le=10, description="Количество изображений от 0 до 10")
    is_closed: Optional[bool] = False
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None