from app.core.db import get_pool


async def track_upload(file_size: int):
    pool = await get_pool()
    async with pool.acquire() as conn:
        await conn.execute(
            """UPDATE stats
               SET total_uploads = total_uploads + 1,
                   total_upload_bytes = total_upload_bytes + $1
               WHERE id = 1""",
            file_size,
        )


async def track_download(file_size: int):
    pool = await get_pool()
    async with pool.acquire() as conn:
        await conn.execute(
            """UPDATE stats
               SET total_downloads = total_downloads + 1,
                   total_download_bytes = total_download_bytes + $1
               WHERE id = 1""",
            file_size,
        )


async def get_stats() -> dict:
    pool = await get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow("SELECT * FROM stats WHERE id = 1")
    return dict(row) if row else {}
