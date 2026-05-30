import asyncio
from app.services.file_service import delete_expired_files

CLEANUP_INTERVAL = 300  # Run every 5 minutes


async def start_cleanup_scheduler():
    """Background task that periodically deletes expired files from R2 and DB."""
    while True:
        try:
            await delete_expired_files()
        except Exception as e:
            print(f"Cleanup scheduler error: {e}")
        await asyncio.sleep(CLEANUP_INTERVAL)
