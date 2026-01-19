from fastapi import APIRouter, HTTPException
import logging
from models.ad_request import AdRequest
from models.ad_response import AdResponse

logger = logging.getLogger(__name__)
router = APIRouter(tags=["Prediction"])

@router.post("/predict", response_model=AdResponse)
async def predict(request: AdRequest, value_error: bool = False) -> AdResponse:
    try:
        logger.info(f'Processing ad moderation for seller: {request.seller_id}')

        if request.is_verified_seller or request.images_qty > 0:
            result = True
            message = 'Advertisement is approved'
        else:
            result = False
            message = 'Advertisement is not approved'
        
        logger.info(f"Ad moderation result for seller_id {request.seller_id}: {result}")

        if value_error:
            logger.info('Business logic error')
            raise ValueError('Simulated business logic error')

        return AdResponse(is_approved=result, message=message)

    except Exception as e:
        logger.error(f'Error processing ad moderation: {str(e)}')
        raise HTTPException(status_code=500, detail=f'Internal server error: {str(e)}')