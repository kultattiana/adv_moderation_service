from typing import Optional, Dict, Any
import asyncpg
from contextlib import asynccontextmanager
import os
import time


from observability.metrics import DB_QUERY_DURATION

@asynccontextmanager
async def get_pg_connection(operation: str = "query"):
    conn = await asyncpg.connect(
        host=os.getenv("DB_HOST", "localhost"),
        port=int(os.getenv("DB_PORT", 5432)),
        user=os.getenv("DB_USER", "postgres"),
        password=os.getenv("DB_PASSWORD", "postgres"),
        database=os.getenv("DB_NAME", "moderation_db")
    )

    start = time.perf_counter()
    try:
        yield conn
    finally:
        duration = time.perf_counter() - start
        DB_QUERY_DURATION.labels(operation=operation).observe(duration)
        await conn.close()