from fastapi import APIRouter, HTTPException, status, Response, Request
from typing import Sequence, Mapping, Any
from pydantic import BaseModel
from models.ad import AdModel
from services.advertisements import AdvertisementService
from errors import SellerNotFoundError, AdNotFoundError

router = APIRouter(tags=['Ads'])
ad_service = AdvertisementService()

class CreateAdInDto(BaseModel):
    name: str
    description: str
    category: int
    images_qty: int

@router.post('/', status_code=status.HTTP_201_CREATED)
async def create(data: CreateAdInDto, request: Request) -> AdModel:
    data = dict(data)
    current_seller_id = request.cookies.get('x-user-id')
    if not current_seller_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail='Unauthorized',
        )
    data['seller_id'] = int(current_seller_id)
    return await ad_service.create(data)

@router.get('/{item_id}')
async def get_by_item_id(item_id: int) -> AdModel:
    try:
        return await ad_service.get_by_item_id(item_id)
    except AdNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f'Ad {item_id} is not found',
        )

@router.get('/list/{seller_id}')
async def get_by_seller_id(seller_id: int) -> Sequence[AdModel]:
    try:
        return await ad_service.get_by_seller_id(seller_id)
    except SellerNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f'Seller {seller_id} is not found',
        )

@router.delete('/{item_id}')
async def delete(item_id: int, request: Request) -> AdModel:
    current_seller_id = request.cookies.get('x-user-id')

    if not current_seller_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail='Unauthorized',
        )
    try:
        return await ad_service.delete(item_id)
    except AdNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f'Ad {item_id} is not found',
        )
    

@router.get('/', status_code=status.HTTP_200_OK)
async def get_many() -> Sequence[AdModel]:
    return await ad_service.get_many()
    


@router.patch('/update/{item_id}')
async def update_description(item_id: int, 
                            description: str,
                            request: Request) -> AdModel:
    
    current_seller_id = request.cookies.get('x-user-id')

    if not current_seller_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail='Unauthorized',
        )
    
    try:
        return await ad_service.update(item_id, description=description)
    except AdNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f'Item {item_id} is not found',
        )
    