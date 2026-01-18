from fastapi import FastAPI, HTTPException
import uvicorn
from data_models import AdResponse, AdRequest
import logging


logging.basicConfig(level = logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title = 'Ad Moderation Service',
    description = 'Сервис модерации объявлений',
    version = '1.0.0'
)

@app.post("/predict", response_model = AdResponse)
async def predict(request: AdRequest, value_error: bool = False)->AdResponse:
    try:
        logger.info(f'Processing ad moderation for seller: {request.seller_id}')

        if request.is_verified_seller or request.images_qty > 0:
            result = True
            message = 'Advertisment is approved'
        else:
            result = False
            message = 'Advertisment is not approved'
        
        logger.info(f"Ad moderation result for seller_id {request.seller_id}: {result}")

        print(value_error)
        if value_error:
            print(value_error)
            logger.info('Business logic error')
            raise ValueError('Simulated business logic')

        return AdResponse(is_approved = result, message = message)

    except Exception as e:
        logger.error(f'Error processing ad moderation: {str(e)}')
        raise HTTPException(status_code = 500, detail = f'Internal server error: {str(e)}')



if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)