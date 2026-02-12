import sys
sys.path.append('.')
from fastapi import APIRouter, HTTPException, Depends, Request
from models.predict_request import PredictRequest, SimplePredictRequest
from models.predict_response import PredictResponse
from services.predictions import PredictionService
from services.moderations import ModerationService
from errors import ModelNotLoadedError, AdNotFoundError
import logging
from typing import Optional
from pydantic import BaseModel

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Prediction"])

pred_service = PredictionService()
mod_service = ModerationService()

class CreateModerationInDto(BaseModel):
    item_id: int
    status: str
    is_violation: Optional[bool] = None
    probability: Optional[float] = None
    error_message: Optional[str] = None

    
@router.post("/predict", response_model = PredictResponse)
async def predict(request: PredictRequest) -> PredictResponse:
    try:      
        logger.info(f"""Processing ad moderation request: seller_id - {request.seller_id}, item_id - {request.item_id}, name - {request.name}, 
                            is_verified_seller - {request.is_verified_seller}, description - {request.description}, 
                            category - {request.category}, images_qty - {request.images_qty}
                        """)
        
        is_violation, probability = await pred_service.predict(
                                                            request.seller_id,
                                                            request.is_verified_seller,
                                                            request.item_id,
                                                            request.name,
                                                            request.description,
                                                            request.category,
                                                            request.images_qty)
        logger.info(
            f"Ad moderation for seller_id {request.seller_id} item {request.item_id} (name: '{request.name}...'): "
            f"violation={is_violation}, probability={probability:.3f}"
        )
        return PredictResponse(is_violation=is_violation, probability = probability)
    
    except ModelNotLoadedError:
        raise HTTPException(
                status_code=503,
                detail="Model is not loaded. Service temporarily unavailable."
            )
    except Exception as e:
        logger.error(f'Error processing ad moderation: {str(e)}')
        raise HTTPException(status_code=500, detail=f'Internal server error: {str(e)}')
    

@router.post("/simple_predict/{item_id}", response_model=PredictResponse)
async def simple_predict(request: SimplePredictRequest) -> PredictResponse:

    try:
        logger.info(f"""Processing ad moderation request: item_id - {request.item_id}""")
        is_violation, probability = await pred_service.simple_predict(request.item_id)
        logger.info(
            f"Ad moderation for item {request.item_id}: "
            f"violation={is_violation}, probability={probability:.3f}"
        )
        return PredictResponse(is_violation=is_violation, probability = probability)
        
    except AdNotFoundError:
        raise HTTPException(
            status_code=404,
            detail=f"Advertisement with ID {request.item_id} is not found"
        )
    except ModelNotLoadedError:
        raise HTTPException(
                status_code=503,
                detail="Model is not loaded. Service temporarily unavailable."
            )
    except Exception as e:
        logger.error(f'Error processing ad moderation: {str(e)}')
        raise HTTPException(status_code=500, detail=f'Internal server error: {str(e)}')
