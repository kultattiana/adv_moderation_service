from fastapi import Request
from dependencies import AuthServiceDepend
from fastapi import APIRouter, HTTPException, status, Response, Request
from typing import Sequence, Mapping, Any
from pydantic import BaseModel, Field
from errors import UnauthorizedError, AccountBlockedError
from routers.health import sentry_sdk


async def auth(request: Request, auth_service: AuthServiceDepend):
    try:
        x_user_token = request.cookies.get('x-user-token')
        return await auth_service.verify(x_user_token)
    except UnauthorizedError as e:

        sentry_sdk.capture_message(
            "Unauthorized access to current seller endpoint",
            level="warning"
        )

        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail='Unauthorized',
        )
    except AccountBlockedError as e:

        sentry_sdk.capture_message(
            "Account is blocked",
            level="warning"
        )

        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail='Account is blocked',
        )