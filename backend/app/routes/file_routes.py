from fastapi import APIRouter, UploadFile, File
from app.controllers import file_controller
from app.schemas.file_schema import (
    UploadInitiateRequest,
    UploadInitiateResponse,
    UploadCompleteRequest,
    FileUploadResponse,
    DownloadFileResponse,
    StatsResponse,
    ErrorResponse,
)
from app.services import stats_service

router = APIRouter()


@router.post(
    "/upload/initiate",
    status_code=200,
    response_model=UploadInitiateResponse,
    responses={
        400: {"model": ErrorResponse},
        413: {"model": ErrorResponse},
        500: {"model": ErrorResponse},
    },
)
async def initiate_upload(body: UploadInitiateRequest):
    """Initiate a multipart upload. Returns presigned URLs for each chunk."""
    return await file_controller.initiate_upload(body)


@router.post(
    "/upload/complete",
    status_code=201,
    response_model=FileUploadResponse,
    responses={
        400: {"model": ErrorResponse},
        500: {"model": ErrorResponse},
    },
)
async def complete_upload(body: UploadCompleteRequest):
    """Complete a multipart upload after all chunks are uploaded to R2."""
    return await file_controller.complete_upload(body)


@router.post(
    "/upload",
    status_code=201,
    response_model=FileUploadResponse,
    responses={
        400: {"model": ErrorResponse},
        413: {"model": ErrorResponse},
        500: {"model": ErrorResponse},
    },
)
async def upload(file: UploadFile = File(...)):
    """Direct upload for small files (< 5 MB)."""
    return await file_controller.upload(file)


@router.get(
    "/stats",
    response_model=StatsResponse,
)
async def get_stats():
    """Get upload/download tracking stats."""
    data = await stats_service.get_stats()
    return StatsResponse(
        total_uploads=data.get("total_uploads", 0),
        total_downloads=data.get("total_downloads", 0),
        total_upload_bytes=data.get("total_upload_bytes", 0),
        total_download_bytes=data.get("total_download_bytes", 0),
    )


@router.get(
    "/{key}",
    response_model=DownloadFileResponse,
    responses={
        400: {"model": ErrorResponse},
        404: {"model": ErrorResponse},
    },
)
async def get_file(key: str):
    """Get file info by UUID or 6-digit access key."""
    return await file_controller.get_file(key)
