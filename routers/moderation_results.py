from fastapi import APIRouter, HTTPException, status, Response, Request
from typing import Sequence, Mapping, Any
from services.moderations import ModerationService
from errors import ModerationNotFoundError
from models.moderation_result import ErrorModerationResultResponse, ModerationResultResponse
from models.moderation import ModerationModel
import logging
from routers.health import sentry_sdk

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Moderation Results"])
mod_service = ModerationService()

@router.get('/{task_id}')
async def get_by_task_id(task_id: int):

    with sentry_sdk.configure_scope() as scope:
        scope.set_tag("endpoint", "get_moderation_by_task_id")
        scope.set_tag("http_method", "GET")
        scope.set_context("request_data", {
            "task_id": task_id
        })

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

            sentry_sdk.capture_message(
                f"Failed moderation detected for task {task_id}",
                level="warning",
                extras={
                    "task_id": task_id,
                    "error_message": mod_result.error_message
                }
            )

            return ErrorModerationResultResponse(**response_data)
        else:
            return ModerationResultResponse(**response_data)

    except ModerationNotFoundError as e:

        sentry_sdk.capture_exception(e)
        sentry_sdk.set_tag("error_type", "moderation_not_found")
        sentry_sdk.set_context("error_details", {
            "task_id": task_id
        })

        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f'Moderation result from task {task_id} is not found',
        )

@router.delete('/{task_id}')
async def delete(task_id: int, request: Request) -> ModerationModel:

    with sentry_sdk.configure_scope() as scope:
        scope.set_tag("endpoint", "delete_moderation")
        scope.set_tag("http_method", "DELETE")
        scope.set_context("request_data", {
            "task_id": task_id
        })
        
        user_id = request.cookies.get('x-user-id')
        if user_id:
            scope.set_user({"id": user_id})

    try:
        return await mod_service.delete(task_id)
    except ModerationNotFoundError as e:

        sentry_sdk.capture_exception(e)
        sentry_sdk.set_tag("error_type", "moderation_not_found")
        sentry_sdk.set_context("error_details", {
            "task_id": task_id
        })

        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f'Task {task_id} is not found',
        )

@router.get('/', status_code=status.HTTP_200_OK)
async def get_many() -> Sequence[ModerationModel]:
    return await mod_service.get_many()