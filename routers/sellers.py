from fastapi import APIRouter, HTTPException, status, Response, Request, Depends
from typing import Sequence
from pydantic import BaseModel
from models.seller import SellerModel
from services.sellers import SellerService
from services.auth import AuthService
from errors import SellerNotFoundError, UnauthorizedError, AccountBlockedError
from dependencies import AuthServiceDepend, SellerServiceDepend
import asyncpg
from routers.health import sentry_sdk
from typing import Annotated
from auth_middleware.auth import auth

class CreateSellerInDto(BaseModel):
    username: str
    email: str
    password: str
    is_verified: bool = False

class LoginUserInDto(BaseModel):
    login: str
    password: str

    
router = APIRouter(tags=['Sellers'])
root_router = APIRouter(tags = ['Login'])


@router.get('/', status_code=status.HTTP_200_OK)
async def get_many(seller_service: SellerServiceDepend) -> Sequence[SellerModel]:
    return await seller_service.get_many()


@router.post('/', status_code=status.HTTP_201_CREATED)
async def register(data: CreateSellerInDto, seller_service: SellerServiceDepend) -> SellerModel:

    with sentry_sdk.configure_scope() as scope:
        scope.set_tag("endpoint", "register_seller")
        scope.set_tag("http_method", "POST")
        scope.set_context("request_data", {
            "username": data.username,
            "email": data.email,
            "password": data.password,
            "is_verified": data.is_verified
        })

    try:
        result =  await seller_service.register(dict(data))
        return result
    except asyncpg.exceptions.UniqueViolationError as e:

        sentry_sdk.capture_exception(e)
        sentry_sdk.set_tag("error_type", "unique_violation")
        sentry_sdk.set_context("error_details", {
            "email": data.email,
            "username": data.username
        })

        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="This seller is already registered"
        )


@router.get('/{seller_id}')
async def get_by_seller_id(seller_id: int, seller_service: SellerServiceDepend) -> SellerModel:

    with sentry_sdk.configure_scope() as scope:
        scope.set_tag("endpoint", "get_seller_by_id")
        scope.set_tag("http_method", "GET")
        scope.set_context("request_data", {
            "seller_id": seller_id
        })

    try:
        result =  await seller_service.get_by_seller_id(seller_id)
        return result
    except SellerNotFoundError as e:

        sentry_sdk.capture_exception(e)
        sentry_sdk.set_tag("error_type", "seller_not_found")
        sentry_sdk.set_context("error_details", {
            "seller_id": seller_id
        })

        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f'User {seller_id} is not found',
        )


@router.get('/current/')
async def get_current(current_seller: Annotated[SellerModel, Depends(auth)],
                      seller_service: SellerServiceDepend) -> SellerModel:

    with sentry_sdk.configure_scope() as scope:
        scope.set_tag("endpoint", "get_current_seller")
        scope.set_tag("http_method", "GET")
        scope.set_context("request_data", {
            "has_cookie": current_seller.seller_id is not None
        })
    
    sentry_sdk.set_user({"id": current_seller.seller_id})

    try:
        result = await seller_service.get_by_seller_id(int(current_seller.seller_id))
        return result
    except SellerNotFoundError as e:

        sentry_sdk.capture_exception(e)
        sentry_sdk.set_tag("error_type", "seller_not_found")
        sentry_sdk.set_context("error_details", {
            "seller_id": current_seller.seller_id
        })

        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f'User {current_seller.seller_id} is not found',
        )


@router.patch('/verify/{seller_id}')
async def verify(seller_id: int, 
                 seller_service: SellerServiceDepend,
                 seller: Annotated[SellerModel, Depends(auth)],) -> SellerModel:

    with sentry_sdk.configure_scope() as scope:
        scope.set_tag("endpoint", "verify_seller")
        scope.set_tag("http_method", "PATCH")
        scope.set_context("request_data", {
            "seller_id": seller_id
        })

    try:
        result =  await seller_service.verify(int(seller_id))
        return result
    
    except SellerNotFoundError as e:

        sentry_sdk.capture_exception(e)
        sentry_sdk.set_tag("error_type", "seller_not_found")
        sentry_sdk.set_context("error_details", {
            "seller_id": seller_id
        })

        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f'User {seller_id} is not found',
        )


@router.delete('/{seller_id}')
async def delete(seller_id: int, 
                 seller_service: SellerServiceDepend,
                 _: Annotated[SellerModel, Depends(auth)]) -> SellerModel:

    with sentry_sdk.configure_scope() as scope:
        scope.set_tag("endpoint", "delete_seller")
        scope.set_tag("http_method", "DELETE")
        scope.set_context("request_data", {
            "seller_id": seller_id
        })

    try:
        result =  await seller_service.delete(seller_id)
        return result
    except SellerNotFoundError as e:

        sentry_sdk.capture_exception(e)
        sentry_sdk.set_tag("error_type", "seller_not_found")
        sentry_sdk.set_context("error_details", {
            "seller_id": seller_id
        })

        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f'User {seller_id} is not found',
        )


@root_router.post('/login')
async def login(
    dto: LoginUserInDto,
    response: Response,
    auth_service: AuthServiceDepend
):
    
    with sentry_sdk.configure_scope() as scope:
        scope.set_tag("endpoint", "login")
        scope.set_tag("http_method", "POST")
        scope.set_context("request_data", {
            "login": dto.login,
        })

    try:
        user_token, seller = await auth_service.login(dto.login, dto.password)

        response.set_cookie(
            key="x-user-token",
            value=user_token,
            secure=True,
        )

        response.status_code = status.HTTP_200_OK

        sentry_sdk.set_user({"id": seller.seller_id})

        return seller

    except ValueError as e:

        sentry_sdk.capture_exception(e)
        sentry_sdk.set_tag("error_type", "invalid_credentials")
        sentry_sdk.set_context("error_details", {
            "login": dto.login,
        })

        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f'Login or password is wrong',
        )
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