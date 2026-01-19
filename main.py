from fastapi import FastAPI, HTTPException
import uvicorn
from routers import health, predict

app = FastAPI(
    title = 'Ad Moderation Service',
    description = 'Сервис модерации объявлений',
    version = '1.0.0'
)

app.include_router(health.router)
app.include_router(predict.router)


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)