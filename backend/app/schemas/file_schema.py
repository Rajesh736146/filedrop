from pydantic import BaseModel
from datetime import datetime
from uuid import UUID


# --- Upload Initiate ---
class UploadInitiateRequest(BaseModel):
    file_name: str
    file_size: int  # in bytes
    content_type: str = "application/octet-stream"


class UploadInitiateResponse(BaseModel):
    upload_id: str
    r2_key: str
    part_urls: list[str]
    num_parts: int
    chunk_size: int


# --- Upload Complete ---
class PartInfo(BaseModel):
    part_number: int
    etag: str


class UploadCompleteRequest(BaseModel):
    upload_id: str
    r2_key: str
    file_name: str
    file_size: int
    content_type: str
    parts: list[PartInfo]


class FileUploadResponse(BaseModel):
    id: UUID
    name: str
    size: int
    content_type: str
    download_url: str
    access_key: str
    expires_at: datetime
    created_at: datetime


# --- Download ---
class DownloadFileResponse(BaseModel):
    id: UUID
    name: str
    size: int
    content_type: str
    download_url: str
    access_key: str
    expires_at: datetime


# --- File Metadata ---
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


# --- Stats ---
class StatsResponse(BaseModel):
    total_uploads: int
    total_downloads: int
    total_upload_bytes: int
    total_download_bytes: int


# --- Common ---
class HealthResponse(BaseModel):
    status: str


class ErrorResponse(BaseModel):
    detail: str
