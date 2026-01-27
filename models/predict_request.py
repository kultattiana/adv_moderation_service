from pydantic import BaseModel, Field
from typing import Optional

class PredictRequest(BaseModel):
    seller_id: int = Field(..., gt = 0, description = 'Положительный ID продавца')
    is_verified_seller: bool = Field(..., description = 'Статус верификации продавца')
    item_id: int = Field(..., gt = 0, description = 'Положительный ID товара')
    name: str = Field(..., min_length = 1, max_length = 500, description = 'Название товара')
    description: str = Field(..., min_length = 1, max_length = 1000, description = 'Описание товара')
    category: int = Field(..., ge = 0, le = 100, description = 'Категория товара (от 0 до 100)')
    images_qty: int = Field(..., ge=0, le=10, description="Количество изображений от 0 до 10")