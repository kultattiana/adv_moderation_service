import redis.asyncio as redis
from typing import AsyncGenerator
from contextlib import asynccontextmanager


@asynccontextmanager
async def get_redis_connection() -> AsyncGenerator[redis.Redis, None]:
    connection = redis.Redis(host="localhost", port=6379)

    yield connection

    await connection.aclose()