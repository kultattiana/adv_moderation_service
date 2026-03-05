from fastapi import APIRouter, HTTPException, status, Response, Request
from typing import Sequence, Mapping, Any
from pydantic import BaseModel, Field
from models.ad import AdModel
from services.advertisements import AdvertisementService
from errors import SellerNotFoundError, AdNotFoundError

router = APIRouter(tags=['Ads'])
ad_service = AdvertisementService()

from routers.health import sentry_sdk

class CreateAdInDto(BaseModel):
    name: str = Field(..., min_length = 1, max_length = 500, description = 'Название товара')
    description: str = Field(..., min_length = 1, max_length = 1000, description = 'Описание товара')
    category: int = Field(..., ge = 0, le = 100, description = 'Категория товара (от 0 до 100)')
    images_qty: int = Field(..., ge=0, le=10, description="Количество изображений от 0 до 10")

@router.post('/', status_code=status.HTTP_201_CREATED)
async def create(data: CreateAdInDto, request: Request) -> AdModel:

    with sentry_sdk.configure_scope() as scope:
        scope.set_tag("endpoint", "create_ad")
        scope.set_tag("http_method", "POST")
        scope.set_context("request_data", {
            "name": data.name,
            "category": data.category,
            "images_qty": data.images_qty
        })

    try:
        data = dict(data)
        current_seller_id = request.cookies.get('x-user-id')
        if not current_seller_id:
            sentry_sdk.capture_message(
                "Unauthorized attempt to create ad",
                level="warning"
            )
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail='Unauthorized',
            )
        data['seller_id'] = int(current_seller_id)
        sentry_sdk.set_user({"id": current_seller_id})
    
        result =  await ad_service.create(data)
        return result
    
    except SellerNotFoundError as e:

        sentry_sdk.capture_exception(e)
        sentry_sdk.set_tag("error_type", "seller_not_found")
        sentry_sdk.set_context("error_details", {
            "seller_id": current_seller_id if 'current_seller_id' in locals() else None
        })
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail='Unauthorized',
        )

@router.get('/{item_id}')
async def get_by_item_id(item_id: int) -> AdModel:

    with sentry_sdk.configure_scope() as scope:
        scope.set_tag("endpoint", "get_ad_by_id")
        scope.set_tag("http_method", "GET")
        scope.set_context("request_data", {
            "item_id": item_id
        })

    try:
        result =  await ad_service.get_by_item_id(item_id)
        return result
    except AdNotFoundError as e:

        sentry_sdk.capture_exception(e)
        sentry_sdk.set_tag("error_type", "ad_not_found")
        sentry_sdk.set_context("error_details", {
            "item_id": item_id
        })

        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f'Ad {item_id} is not found',
        )

@router.get('/list/{seller_id}')
async def get_by_seller_id(seller_id: int) -> Sequence[AdModel]:

    with sentry_sdk.configure_scope() as scope:
        scope.set_tag("endpoint", "get_ads_by_seller")
        scope.set_tag("http_method", "GET")
        scope.set_context("request_data", {
            "seller_id": seller_id
        })

    try:
        result =  await ad_service.get_by_seller_id(seller_id)
        return result
    except SellerNotFoundError as e:

        sentry_sdk.capture_exception(e)
        sentry_sdk.set_tag("error_type", "seller_not_found")
        sentry_sdk.set_context("error_details", {
            "seller_id": seller_id
        })

        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f'Seller {seller_id} is not found',
        )

@router.delete('/{item_id}')
async def delete(item_id: int, request: Request) -> AdModel:
    current_seller_id = request.cookies.get('x-user-id')

    with sentry_sdk.configure_scope() as scope:
        scope.set_tag("endpoint", "delete_ad")
        scope.set_tag("http_method", "DELETE")
        scope.set_context("request_data", {
            "item_id": item_id,
            "seller_id": current_seller_id
        })

    if not current_seller_id:
        sentry_sdk.capture_message(
            "Unauthorized attempt to delete ad",
            level="warning",
            extras={"item_id": item_id}
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail='Unauthorized',
        )
    sentry_sdk.set_user({"id": current_seller_id})
    try:
        ad = await ad_service.get_by_item_id(item_id)
        if ad.seller_id != int(current_seller_id):
            sentry_sdk.capture_message(
                "Attempt to delete ad belonging to another seller",
                level="warning",
                extras={
                    "item_id": item_id,
                    "request_seller": current_seller_id,
                    "ad_seller": ad.seller_id
                }
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You can only delete your own ads",
            )
        
        result = await ad_service.delete(item_id)
        return result
    
    except AdNotFoundError as e:

        sentry_sdk.capture_exception(e)
        sentry_sdk.set_tag("error_type", "ad_not_found")
        sentry_sdk.set_context("error_details", {
            "item_id": item_id
        })

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

    with sentry_sdk.configure_scope() as scope:
        scope.set_tag("endpoint", "update_ad")
        scope.set_tag("http_method", "PATCH")
        scope.set_context("request_data", {
            "item_id": item_id,
            "seller_id": current_seller_id
        })

    if not current_seller_id:

        sentry_sdk.capture_message(
            "Unauthorized attempt to update ad",
            level="warning",
            extras={"item_id": item_id}
        )

        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail='Unauthorized',
        )
    
    sentry_sdk.set_user({"id": current_seller_id})
    
    try:
        ad = await ad_service.get_by_item_id(item_id)
        if ad.seller_id != int(current_seller_id):
            sentry_sdk.capture_message(
                "Attempt to update ad belonging to another seller",
                level="warning",
                extras={
                    "item_id": item_id,
                    "request_seller": current_seller_id,
                    "ad_seller": ad.seller_id
                }
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You can only update your own ads",
            )
        result = await ad_service.update(item_id, description=description)
        return result
    
    except AdNotFoundError as e:

        sentry_sdk.capture_exception(e)
        sentry_sdk.set_tag("error_type", "ad_not_found")
        sentry_sdk.set_context("error_details", {
            "item_id": item_id
        })

        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f'Item {item_id} is not found',
        )

@router.patch('/close/{item_id}')
async def close(item_id: int, request: Request) -> AdModel:
    
    current_seller_id = request.cookies.get('x-user-id')

    with sentry_sdk.configure_scope() as scope:
        scope.set_tag("endpoint", "close_ad")
        scope.set_tag("http_method", "PATCH")
        scope.set_context("request_data", {
            "item_id": item_id,
            "seller_id": current_seller_id
        })

    if not current_seller_id:
        sentry_sdk.capture_message(
            "Unauthorized attempt to close ad",
            level="warning",
            extras={"item_id": item_id}
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail='Unauthorized',
        )

    sentry_sdk.set_user({"id": current_seller_id})
    
    try:
        ad = await ad_service.get_by_item_id(item_id)
        if ad.seller_id != int(current_seller_id):
            sentry_sdk.capture_message(
                "Attempt to close ad belonging to another seller",
                level="warning",
                extras={
                    "item_id": item_id,
                    "request_seller": current_seller_id,
                    "ad_seller": ad.seller_id
                }
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You can only close your own ads",
            )
        
        result = await ad_service.close(item_id)
        return result
    
    except AdNotFoundError as e:

        sentry_sdk.capture_exception(e)
        sentry_sdk.set_tag("error_type", "ad_not_found")
        sentry_sdk.set_context("error_details", {
            "item_id": item_id
        })
    
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f'Item {item_id} is not found',
        )
    