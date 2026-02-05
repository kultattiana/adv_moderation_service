from fastapi import APIRouter, HTTPException, status, Response, Request
from typing import Sequence
from pydantic import BaseModel
from models.seller import SellerModel
from services.sellers import SellerService
from errors import SellerNotFoundError
import asyncpg

class CreateSellerInDto(BaseModel):
    username: str
    email: str
    password: str
    is_verified: bool = False

class LoginUserInDto(BaseModel):
    email: str
    password: str

    
router = APIRouter(tags=['Sellers'])
root_router = APIRouter(tags = ['Login'])

seller_service = SellerService()


@router.get('/', status_code=status.HTTP_200_OK)
async def get_many() -> Sequence[SellerModel]:
    return await seller_service.get_many()


@router.post('/', status_code=status.HTTP_201_CREATED)
async def register(data: CreateSellerInDto) -> SellerModel:
    try:
        return await seller_service.register(dict(data))
    except asyncpg.exceptions.UniqueViolationError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="This seller is already registered"
        )


@router.get('/{seller_id}')
async def get_by_seller_id(seller_id: int) -> SellerModel:
    try:
        return await seller_service.get_by_seller_id(seller_id)
    except SellerNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f'User {seller_id} is not found',
        )


@router.get('/current/')
async def get_current(request: Request) -> SellerModel:
    current_seller_id = request.cookies.get('x-user-id')
    if not current_seller_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail='Unauthorized',
        )

    try:
        return await seller_service.get_by_seller_id(int(current_seller_id))
    except SellerNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f'User {current_seller_id} is not found',
        )

@router.patch('/verify/{seller_id}')
async def verify(seller_id: int, request: Request) -> SellerModel:
    try:
        return await seller_service.verify(int(seller_id))
    except SellerNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f'User {seller_id} is not found',
        )


@router.delete('/{seller_id}')
async def delete(seller_id: int, request: Request) -> SellerModel:
    try:
        return await seller_service.delete(seller_id)
    except SellerNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f'User {seller_id} is not found',
        )


@root_router.post('/login')
async def login(
    dto: LoginUserInDto,
    response: Response,
) -> SellerModel:
    try:
        seller = await seller_service.login(dto.email, dto.password)

        response.set_cookie(
            key="x-user-id",
            value=seller.seller_id,
        )

        return seller
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f'Login or password is wrong',
        )