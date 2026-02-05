from fastapi import FastAPI, HTTPException
import uvicorn
from routers import health, predict, ads, sellers
from contextlib import asynccontextmanager
from typing import AsyncIterator
import os
import warnings
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)


from model import model_singleton

@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    use_mlflow = os.getenv("USE_MLFLOW", "false").strip().lower() == "true"
    source = "MLflow" if use_mlflow else "local file"
    logger.info(f"Loading model from: {source}")
    logger.info(f"Model loaded: {model_singleton.is_loaded}")
    yield

app = FastAPI(
    title = 'Ad Moderation Service',
    description = 'Сервис модерации объявлений',
    version = '1.0.0',
    lifespan = lifespan
)


app.include_router(health.router)
app.include_router(predict.router)
app.include_router(ads.router, prefix='/ads')
app.include_router(sellers.router, prefix='/sellers')
app.include_router(sellers.root_router)


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)