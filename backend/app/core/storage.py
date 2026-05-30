import asyncio
from contextlib import asynccontextmanager
from aiobotocore.session import get_session
from botocore.config import Config
from app.config.settings import R2_ACCOUNT_ID, R2_ACCESS_KEY_ID, R2_SECRET_ACCESS_KEY, R2_BUCKET_NAME

BUCKET_NAME = R2_BUCKET_NAME

_session = get_session()

_client_config = Config(
    signature_version="s3v4",
    max_pool_connections=100,
    connect_timeout=10,
    read_timeout=30,
    retries={"max_attempts": 3, "mode": "adaptive"},
)


@asynccontextmanager
async def get_r2_client():
    async with _session.create_client(
        "s3",
        endpoint_url=f"https://{R2_ACCOUNT_ID}.r2.cloudflarestorage.com",
        aws_access_key_id=R2_ACCESS_KEY_ID,
        aws_secret_access_key=R2_SECRET_ACCESS_KEY,
        region_name="auto",
        config=_client_config,
    ) as client:
        yield client


async def upload(key: str, data: bytes, content_type: str) -> dict:
    async with get_r2_client() as client:
        await client.put_object(
            Bucket=BUCKET_NAME,
            Key=key,
            Body=data,
            ContentType=content_type,
        )
    return {"key": key, "content_type": content_type}


async def upload_streaming(key: str, file_obj, content_type: str, size: int) -> dict:
    """Upload using streaming for large files — avoids loading entire file in memory."""
    async with get_r2_client() as client:
        await client.put_object(
            Bucket=BUCKET_NAME,
            Key=key,
            Body=file_obj,
            ContentType=content_type,
            ContentLength=size,
        )
    return {"key": key, "content_type": content_type}


async def generate_presigned_url(key: str, expires_in: int = 18000) -> str:
    """Generate a presigned download URL. Default expiry: 5 hours (18000s)."""
    async with get_r2_client() as client:
        url = await client.generate_presigned_url(
            "get_object",
            Params={"Bucket": BUCKET_NAME, "Key": key},
            ExpiresIn=expires_in,
        )
    return url


async def remove(key: str) -> None:
    async with get_r2_client() as client:
        await client.delete_object(Bucket=BUCKET_NAME, Key=key)


async def remove_batch(keys: list[str]) -> None:
    """Delete multiple objects in parallel for faster cleanup."""
    semaphore = asyncio.Semaphore(20)

    async def _delete(key):
        async with semaphore:
            await remove(key)

    await asyncio.gather(*[_delete(k) for k in keys], return_exceptions=True)
