from fastapi import APIRouter, HTTPException
import logging
from models.ad_request import AdRequest
from models.ad_response import AdResponse
from services.advertisements import AdvertisementService

logger = logging.getLogger(__name__)
router = APIRouter(tags=["Prediction"])

adv_service = AdvertisementService()

@router.post("/predict")
async def predict(request: AdRequest) -> bool:
    try:
        logger.info(f'Processing ad moderation for seller: {request.seller_id}')

        result = await adv_service.predict(request.is_verified_seller, request.images_qty)

        logger.info(f"Ad moderation result for seller_id {request.seller_id}: {result}")

        # if value_error:
        #     logger.info('Business logic error')
        #     raise ValueError('Simulated business logic error')

        #return AdResponse(is_approved=result)
        return result

    except Exception as e:
        logger.error(f'Error processing ad moderation: {str(e)}')
        raise HTTPException(status_code=500, detail=f'Internal server error: {str(e)}')