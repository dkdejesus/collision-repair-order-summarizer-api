import logging
import time
import uuid
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse

from app.config import get_settings
from app.logging_config import configure_logging
from app.repository import RepairOrderSummaryRepository
from app.schemas import RepairOrderSummaryListResponse, RepairOrderSummaryRequest, RepairOrderSummaryResponse, StoredRepairOrderSummary
from app.service import RepairOrderSummaryService

settings = get_settings()
configure_logging(settings.log_level)
logger = logging.getLogger("collision_repair_order_summarizer_api")
service = RepairOrderSummaryService(settings)
repository = RepairOrderSummaryRepository(settings.database_path)


@asynccontextmanager
async def lifespan(_: FastAPI):
    repository.initialize()
    logger.info("application_started")
    yield
    logger.info("application_stopped")


app = FastAPI(title=settings.app_name, version="0.1.0", lifespan=lifespan)


@app.middleware("http")
async def request_logging(request: Request, call_next):
    request_id = request.headers.get("x-request-id", str(uuid.uuid4()))
    started = time.perf_counter()
    try:
        response = await call_next(request)
    except Exception:
        logger.exception("unhandled_request_error", extra={"request_id": request_id, "path": request.url.path})
        return JSONResponse(status_code=500, content={"detail": "Internal server error", "request_id": request_id})
    duration_ms = round((time.perf_counter() - started) * 1000, 2)
    response.headers["x-request-id"] = request_id
    logger.info(
        "request_completed",
        extra={
            "request_id": request_id,
            "path": request.url.path,
            "duration_ms": duration_ms,
            "status_code": response.status_code,
        },
    )
    return response


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok", "environment": settings.app_env}


@app.post("/v1/repair-order-summaries", response_model=RepairOrderSummaryResponse, status_code=201)
async def create_record(payload: RepairOrderSummaryRequest, request: Request) -> RepairOrderSummaryResponse:
    request_id = request.headers.get("x-request-id", str(uuid.uuid4()))
    try:
        assessment = await service.assess(payload)
    except Exception as exc:
        logger.exception("assessment_failed", extra={"request_id": request_id})
        raise HTTPException(status_code=502, detail="Assessment provider failed") from exc
    model = settings.openai_model if service.client else "rule-based-fallback"
    repository.save(request_id=request_id, request=payload, assessment=assessment, model=model)
    return RepairOrderSummaryResponse(request_id=request_id, assessment=assessment, model=model)


@app.get("/v1/repair-order-summaries", response_model=RepairOrderSummaryListResponse)
async def list_records(limit: int = 20) -> RepairOrderSummaryListResponse:
    safe_limit = max(1, min(limit, 100))
    return RepairOrderSummaryListResponse(records=repository.list_recent(limit=safe_limit))


@app.get("/v1/repair-order-summaries/{request_id}", response_model=StoredRepairOrderSummary)
async def get_record(request_id: str) -> StoredRepairOrderSummary:
    record = repository.get(request_id)
    if record is None:
        raise HTTPException(status_code=404, detail="Record not found")
    return record
