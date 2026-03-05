from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse
import uvicorn
from routers import health, async_predict, ads, sellers, moderation_results, predict
from routers.health import sentry_sdk
from contextlib import asynccontextmanager
from typing import AsyncIterator
import os
import warnings
import logging
from clients.kafka import kafka_producer
from kafka_settings import KAFKA_BOOTSTRAP
from observability import middleware
from observability.middleware import PrometheusMiddleware




logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    logger.info(f"Configuring Kafka Producer with servers: {KAFKA_BOOTSTRAP}")
    await kafka_producer.configure(KAFKA_BOOTSTRAP)
    logger.info("Starting Kafka Producer...")
    await kafka_producer.start()
    yield
    logger.info("Stopping Kafka Producer...")
    await kafka_producer.stop()

app = FastAPI(
    title = 'Ad Moderation Service',
    description = 'Сервис модерации объявлений',
    version = '1.0.0',
    lifespan = lifespan
)

@app.exception_handler(HTTPException)
async def http_exception_sentry_handler(request: Request, exc: HTTPException):
    if exc.status_code >= 500 and sentry_sdk is not None:
        sentry_sdk.capture_exception(exc)
    return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail})


app.include_router(health.router)
app.include_router(async_predict.router)
app.include_router(predict.router)
app.include_router(ads.router, prefix='/ads')
app.include_router(sellers.router, prefix='/sellers')
app.include_router(sellers.root_router)
app.include_router(moderation_results.router, prefix = '/moderation_results')
app.include_router(middleware.router)
app.add_middleware(PrometheusMiddleware)


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)