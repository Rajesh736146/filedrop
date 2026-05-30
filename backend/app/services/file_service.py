import uuid
import os
import math
import random
import string
import asyncio
from datetime import datetime, timedelta
from fastapi import UploadFile
from app.core.db import get_pool
from app.core import storage
from app.core import cache
from app.services import stats_service

EXPIRY_HOURS = 5
_upload_semaphore = asyncio.Semaphore(50)


def _generate_access_key() -> str:
    """Generate a random 6-digit alphanumeric access key."""
    chars = string.ascii_uppercase + string.digits
    return "".join(random.choices(chars, k=6))


async def initiate_upload(file_name: str, file_size: int, content_type: str, chunk_size: int) -> dict:
    """Initiate a multipart upload and return presigned URLs for each chunk."""
    ext = os.path.splitext(file_name)[1]
    r2_key = f"uploads/{uuid.uuid4()}{ext}"

    num_parts = math.ceil(file_size / chunk_size)

    # Start multipart upload on R2
    upload_id = await storage.initiate_multipart_upload(r2_key, content_type)

    # Generate presigned URLs for each part
    part_urls = await storage.generate_presigned_part_urls(r2_key, upload_id, num_parts)

    return {
        "upload_id": upload_id,
        "r2_key": r2_key,
        "part_urls": part_urls,
        "num_parts": num_parts,
        "chunk_size": chunk_size,
    }


async def complete_upload(upload_id: str, r2_key: str, file_name: str, file_size: int, content_type: str, parts: list[dict]) -> dict:
    """Complete a multipart upload and save metadata."""
    # Complete the multipart upload on R2
    await storage.complete_multipart_upload(r2_key, upload_id, parts)

    # Generate presigned download URL (5 hours)
    expires_in_seconds = EXPIRY_HOURS * 3600
    download_url = await storage.generate_presigned_url(r2_key, expires_in=expires_in_seconds)

    access_key = _generate_access_key()

    # Save metadata to PostgreSQL
    pool = await get_pool()
    async with pool.acquire() as conn:
        for _ in range(5):
            try:
                row = await conn.fetchrow(
                    """INSERT INTO files (name, r2_key, content_type, size, download_url, access_key, expires_at)
                       VALUES ($1, $2, $3, $4, $5, $6, NOW() + INTERVAL '5 hours') RETURNING *""",
                    file_name,
                    r2_key,
                    content_type,
                    file_size,
                    download_url,
                    access_key,
                )
                break
            except Exception as e:
                if "unique" in str(e).lower() and "access_key" in str(e).lower():
                    access_key = _generate_access_key()
                else:
                    raise
        else:
            raise Exception("Failed to generate unique access key")

    # Track upload stats
    await stats_service.track_upload(file_size)

    # Cache the file metadata
    result = dict(row)
    await cache.set_cache(f"file:id:{result['id']}", result)
    await cache.set_cache(f"file:key:{result['access_key']}", result)

    return result


async def upload_file(file: UploadFile) -> dict:
    """Direct upload for small files."""
    async with _upload_semaphore:
        ext = os.path.splitext(file.filename)[1]
        r2_key = f"uploads/{uuid.uuid4()}{ext}"

        content = await file.read()
        file_size = len(content)

        await storage.upload(r2_key, content, file.content_type)
        del content

        expires_in_seconds = EXPIRY_HOURS * 3600
        download_url = await storage.generate_presigned_url(r2_key, expires_in=expires_in_seconds)

        access_key = _generate_access_key()

        pool = await get_pool()
        async with pool.acquire() as conn:
            for _ in range(5):
                try:
                    row = await conn.fetchrow(
                        """INSERT INTO files (name, r2_key, content_type, size, download_url, access_key, expires_at)
                           VALUES ($1, $2, $3, $4, $5, $6, NOW() + INTERVAL '5 hours') RETURNING *""",
                        file.filename,
                        r2_key,
                        file.content_type,
                        file_size,
                        download_url,
                        access_key,
                    )
                    break
                except Exception as e:
                    if "unique" in str(e).lower() and "access_key" in str(e).lower():
                        access_key = _generate_access_key()
                    else:
                        raise
            else:
                raise Exception("Failed to generate unique access key")

        await stats_service.track_upload(file_size)

        result = dict(row)
        await cache.set_cache(f"file:id:{result['id']}", result)
        await cache.set_cache(f"file:key:{result['access_key']}", result)

        return result


async def get_file_by_access_key(access_key: str) -> dict | None:
    key = access_key.upper()

    cached = await cache.get_cache(f"file:key:{key}")
    if cached:
        print(f"[CACHE HIT] access_key={key}")
        await stats_service.track_download(cached["size"])
        return cached

    print(f"[CACHE MISS] access_key={key}")
    pool = await get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            "SELECT * FROM files WHERE access_key = $1 AND expires_at > NOW()",
            key,
        )
    if row:
        result = dict(row)
        await stats_service.track_download(result["size"])
        await cache.set_cache(f"file:key:{key}", result)
        await cache.set_cache(f"file:id:{result['id']}", result)
        return result
    return None


async def get_file_by_id(file_id: uuid.UUID) -> dict | None:
    cached = await cache.get_cache(f"file:id:{file_id}")
    if cached:
        print(f"[CACHE HIT] id={file_id}")
        await stats_service.track_download(cached["size"])
        return cached

    print(f"[CACHE MISS] id={file_id}")
    pool = await get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            "SELECT * FROM files WHERE id = $1 AND expires_at > NOW()",
            file_id,
        )
    if row:
        result = dict(row)
        await stats_service.track_download(result["size"])
        await cache.set_cache(f"file:id:{file_id}", result)
        await cache.set_cache(f"file:key:{result['access_key']}", result)
        return result
    return None


async def delete_expired_files():
    """Delete files that have passed their expiry time."""
    pool = await get_pool()
    async with pool.acquire() as conn:
        expired = await conn.fetch(
            "SELECT id, r2_key FROM files WHERE expires_at <= NOW()"
        )
        if not expired:
            return

        keys = [row["r2_key"] for row in expired]
        await storage.remove_batch(keys)

        ids = [row["id"] for row in expired]
        await conn.execute(
            "DELETE FROM files WHERE id = ANY($1::uuid[])", ids
        )

    print(f"Cleaned up {len(expired)} expired file(s)")
