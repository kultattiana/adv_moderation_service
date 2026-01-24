from fastapi import FastAPI, HTTPException
import uvicorn
from routers import health, predict
from model import load_model
from contextlib import asynccontextmanager
from typing import AsyncIterator


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    app.state.model = load_model("model.pkl")
    yield

app = FastAPI(
    title = 'Ad Moderation Service',
    description = 'Сервис модерации объявлений',
    version = '1.0.0',
    lifespan = lifespan
)


app.include_router(health.router)
app.include_router(predict.router)


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)