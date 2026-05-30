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


async def generate_presigned_url(key: str, expires_in: int = 18000) -> str:
    """Generate a presigned download URL. Default expiry: 5 hours (18000s)."""
    async with get_r2_client() as client:
        url = await client.generate_presigned_url(
            "get_object",
            Params={"Bucket": BUCKET_NAME, "Key": key},
            ExpiresIn=expires_in,
        )
    return url


async def generate_presigned_upload_url(key: str, content_type: str, expires_in: int = 3600) -> str:
    """Generate a presigned PUT URL for direct client upload."""
    async with get_r2_client() as client:
        url = await client.generate_presigned_url(
            "put_object",
            Params={
                "Bucket": BUCKET_NAME,
                "Key": key,
                "ContentType": content_type,
            },
            ExpiresIn=expires_in,
        )
    return url


async def initiate_multipart_upload(key: str, content_type: str) -> str:
    """Start a multipart upload and return the upload ID."""
    async with get_r2_client() as client:
        response = await client.create_multipart_upload(
            Bucket=BUCKET_NAME,
            Key=key,
            ContentType=content_type,
        )
    return response["UploadId"]


async def generate_presigned_part_urls(key: str, upload_id: str, num_parts: int, expires_in: int = 3600) -> list[str]:
    """Generate presigned URLs for each part of a multipart upload."""
    async with get_r2_client() as client:
        urls = []
        for part_number in range(1, num_parts + 1):
            url = await client.generate_presigned_url(
                "upload_part",
                Params={
                    "Bucket": BUCKET_NAME,
                    "Key": key,
                    "UploadId": upload_id,
                    "PartNumber": part_number,
                },
                ExpiresIn=expires_in,
            )
            urls.append(url)
    return urls


async def complete_multipart_upload(key: str, upload_id: str, parts: list[dict]) -> dict:
    """Complete a multipart upload with the list of parts (ETag + PartNumber)."""
    async with get_r2_client() as client:
        response = await client.complete_multipart_upload(
            Bucket=BUCKET_NAME,
            Key=key,
            UploadId=upload_id,
            MultipartUpload={
                "Parts": [
                    {"ETag": part["etag"], "PartNumber": part["part_number"]}
                    for part in parts
                ]
            },
        )
    return response


async def abort_multipart_upload(key: str, upload_id: str) -> None:
    """Abort a multipart upload."""
    async with get_r2_client() as client:
        await client.abort_multipart_upload(
            Bucket=BUCKET_NAME,
            Key=key,
            UploadId=upload_id,
        )


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
