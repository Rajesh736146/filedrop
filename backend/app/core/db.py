import asyncpg
import ssl
from app.config.settings import PGHOST, PGDATABASE, PGUSER, PGPASSWORD

pool: asyncpg.Pool | None = None


async def connect_db():
    global pool
    ssl_ctx = ssl.create_default_context()
    ssl_ctx.check_hostname = False
    ssl_ctx.verify_mode = ssl.CERT_NONE

    pool = await asyncpg.create_pool(
        host=PGHOST,
        database=PGDATABASE,
        user=PGUSER,
        password=PGPASSWORD,
        port=5432,
        ssl=ssl_ctx,
        min_size=10,
        max_size=50,
        max_inactive_connection_lifetime=300,
        command_timeout=30,
    )
    print("PostgreSQL connected (pool: 10-50 connections)")


async def disconnect_db():
    global pool
    if pool:
        await pool.close()
        print("PostgreSQL disconnected")


async def init_db():
    global pool
    import os
    ddl_path = os.path.join(os.path.dirname(__file__), "../../ddl.sql")
    with open(ddl_path, "r") as f:
        query = f.read()
    async with pool.acquire() as conn:
        await conn.execute(query)
    print("Database initialized: files table ready")


async def get_pool() -> asyncpg.Pool:
    return pool
