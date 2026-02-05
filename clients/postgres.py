from typing import Optional, Dict, Any
import asyncpg
from contextlib import asynccontextmanager
import os



@asynccontextmanager
async def get_pg_connection():
    conn = await asyncpg.connect(
        host=os.getenv("DB_HOST", "localhost"),
        port=int(os.getenv("DB_PORT", 5432)),
        user=os.getenv("DB_USER", "postgres"),
        password=os.getenv("DB_PASSWORD", "postgres"),
        database=os.getenv("DB_NAME", "moderation_db")
    )
    try:
        yield conn
    finally:
        await conn.close()