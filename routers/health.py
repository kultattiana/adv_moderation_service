from fastapi import APIRouter, Depends
from clients.kafka import kafka_producer
try:
    import sentry_sdk
    from sentry_sdk.integrations.fastapi import FastApiIntegration
    from sentry_sdk.integrations.starlette import StarletteIntegration
except Exception:
    sentry_sdk = None

import os

SENTRY_DSN = os.getenv("SENTRY_DSN", "")

sentry_sdk.init(
    dsn=SENTRY_DSN,
    traces_sample_rate=1.0,
    environment="development",
    integrations=[FastApiIntegration(), StarletteIntegration()],
)

router = APIRouter(tags=["Health"])

@router.get("/health")
def health():
    return {"status": "healthy", "kafka_producer_loaded": kafka_producer._initialized}