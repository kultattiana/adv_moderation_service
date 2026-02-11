from fastapi import APIRouter, HTTPException, status, Response, Request
from typing import Sequence, Mapping, Any
from pydantic import BaseModel
from services.moderations import ModerationService
from errors import ModerationNotFoundError
from models.moderation_result import ErrorModerationResultResponse, ModerationResultResponse
from models.moderation import ModerationModel
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Moderation Results"])
mod_service = ModerationService()

@router.get('/{item_id}')
async def get_by_task_id(task_id: int):
    try:
        mod_result =  await mod_service.get_by_task_id(task_id)
        response_data = {
            "task_id": task_id,
            "status": mod_result.status,
            "is_violation": mod_result.is_violation,
            "probability": mod_result.probability,
        }
        if mod_result.status == "failed":
            response_data["error_message"] = mod_result.error_message
            return ErrorModerationResultResponse(**response_data)
        else:
            return ModerationResultResponse(**response_data)

    except ModerationNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f'Moderation result from task {task_id} is not found',
        )

@router.get('/', status_code=status.HTTP_200_OK)
async def get_many() -> Sequence[ModerationModel]:
    return await mod_service.get_many()