from uuid import UUID
from fastapi import UploadFile, HTTPException
from app.services import file_service
from app.schemas.file_schema import FileUploadResponse, DownloadFileResponse

MAX_FILE_SIZE = 500 * 1024 * 1024  # 500 MB


async def upload(file: UploadFile) -> FileUploadResponse:
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

    # Try parsing as UUID first
    try:
        file_id = UUID(key)
        result = await file_service.get_file_by_id(file_id)
    except ValueError:
        pass

    # If not a UUID, treat as access key
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
