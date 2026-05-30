from pydantic import BaseModel
from datetime import datetime
from uuid import UUID


class FileUploadResponse(BaseModel):
    id: UUID
    name: str
    size: int
    content_type: str
    download_url: str
    access_key: str
    expires_at: datetime
    created_at: datetime


class FileMetadata(BaseModel):
    id: UUID
    name: str
    r2_key: str
    content_type: str
    size: int
    download_url: str
    access_key: str
    expires_at: datetime
    created_at: datetime


class DownloadFileResponse(BaseModel):
    id: UUID
    name: str
    size: int
    content_type: str
    download_url: str
    access_key: str
    expires_at: datetime


class StatsResponse(BaseModel):
    total_uploads: int
    total_downloads: int
    total_upload_bytes: int
    total_download_bytes: int


class HealthResponse(BaseModel):
    status: str


class ErrorResponse(BaseModel):
    detail: str
