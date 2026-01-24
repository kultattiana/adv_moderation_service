from pydantic import BaseModel, Field
from typing import Optional

class AdResponse(BaseModel):
    is_approved: bool = Field(..., description="Результат модерации: True - одобрено, False - отклонено")