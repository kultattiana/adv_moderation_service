from pydantic import BaseModel, Field
from typing import Optional

class PredictResponse(BaseModel):
    is_violation: Optional[bool] = Field(..., description="Результат модерации: True - нарушение, False - нарушений нет")
    probability: Optional[float] = Field(..., ge = 0, le = 1, description = 'Вероятность нарушения')