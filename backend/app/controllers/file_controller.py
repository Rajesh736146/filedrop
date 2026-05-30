from uuid import UUID
from fastapi import UploadFile, HTTPException
from app.services import file_service
from app.schemas.file_schema import (
    UploadInitiateRequest,
    UploadInitiateResponse,
    UploadCompleteRequest,
    FileUploadResponse,
    DownloadFileResponse,
)

MAX_FILE_SIZE = 500 * 1024 * 1024  # 500 MB
CHUNK_SIZE = 5 * 1024 * 1024  # 5 MB per chunk


async def initiate_upload(body: UploadInitiateRequest) -> UploadInitiateResponse:
    if not body.file_name:
        raise HTTPException(status_code=400, detail="File name is required")

    if body.file_size > MAX_FILE_SIZE:
        raise HTTPException(status_code=413, detail="File exceeds 500 MB limit")

    if body.file_size <= 0:
        raise HTTPException(status_code=400, detail="Invalid file size")

    try:
        result = await file_service.initiate_upload(
            file_name=body.file_name,
            file_size=body.file_size,
            content_type=body.content_type,
            chunk_size=CHUNK_SIZE,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Upload initiation failed: {str(e)}")

    return UploadInitiateResponse(**result)


async def complete_upload(body: UploadCompleteRequest) -> FileUploadResponse:
    if not body.parts:
        raise HTTPException(status_code=400, detail="No parts provided")

    try:
        result = await file_service.complete_upload(
            upload_id=body.upload_id,
            r2_key=body.r2_key,
            file_name=body.file_name,
            file_size=body.file_size,
            content_type=body.content_type,
            parts=[{"part_number": p.part_number, "etag": p.etag} for p in body.parts],
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Upload completion failed: {str(e)}")

    return FileUploadResponse(
        id=result["id"],
        name=result["name"],
        size=result["size"],
        content_type=result["content_type"],
        download_url=result["download_url"],
        access_key=result["access_key"],
        expires_at=result["expires_at"],
        created_at=result["created_at"],
    )


async def upload(file: UploadFile) -> FileUploadResponse:
    """Direct upload for small files (< 5 MB)."""
    if not file.filename:
        raise HTTPException(status_code=400, detail="No file provided")

    if file.size and file.size > MAX_FILE_SIZE:
        raise HTTPException(status_code=413, detail="File exceeds 500 MB limit")

    try:
        result = await file_service.upload_file(file)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Upload failed: {str(e)}")

    return FileUploadResponse(
        id=result["id"],
        name=result["name"],
        size=result["size"],
        content_type=result["content_type"],
        download_url=result["download_url"],
        access_key=result["access_key"],
        expires_at=result["expires_at"],
        created_at=result["created_at"],
    )


async def get_file(key: str) -> DownloadFileResponse:
    """Get file by UUID or 6-digit access key."""
    result = None

    try:
        file_id = UUID(key)
        result = await file_service.get_file_by_id(file_id)
    except ValueError:
        pass

    if result is None:
        if len(key) == 6 and key.isalnum():
            result = await file_service.get_file_by_access_key(key)
        else:
            raise HTTPException(status_code=400, detail="Invalid file ID or access key")

    if not result:
        raise HTTPException(status_code=404, detail="File not found or expired")

    return DownloadFileResponse(
        id=result["id"],
        name=result["name"],
        size=result["size"],
        content_type=result["content_type"],
        download_url=result["download_url"],
        access_key=result["access_key"],
        expires_at=result["expires_at"],
    )
