import os
import asyncio
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from app.core.db import connect_db, disconnect_db, init_db
from app.core.cache import connect_redis, disconnect_redis
from app.core.scheduler import start_cleanup_scheduler
from app.routes.file_routes import router as file_router
from app.schemas.file_schema import HealthResponse

IS_VERCEL = os.getenv("VERCEL", False)


@asynccontextmanager
async def lifespan(app: FastAPI):
    await connect_db()
    await init_db()
    await connect_redis()
    cleanup_task = None
    if not IS_VERCEL:
        cleanup_task = asyncio.create_task(start_cleanup_scheduler())
    yield
    if cleanup_task:
        cleanup_task.cancel()
    await disconnect_redis()
    await disconnect_db()


app = FastAPI(title="File Drop", version="1.0.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error"},
    )

app.include_router(file_router, prefix="/api/files", tags=["files"])


@app.get("/health", response_model=HealthResponse)
async def health():
    return HealthResponse(status="ok")


@app.get("/test-upload", response_class=HTMLResponse)
async def test_upload():
    html_path = os.path.join(os.path.dirname(__file__), "..", "test.html")
    with open(html_path, "r") as f:
        return f.read()
