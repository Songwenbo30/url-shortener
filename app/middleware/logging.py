import time
import uuid
import logging
import json
import asyncio
from fastapi import Request, FastAPI
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response
from typing import Any, Dict

logger = logging.getLogger("api")
logger.setLevel(logging.INFO)

if not logger.handlers:
    handler = logging.StreamHandler()
    formatter = logging.Formatter("%(message)s")
    handler.setFormatter(formatter)
    logger.addHandler(handler)


async def log_async(level: int, message: str, extra: Dict[str, Any] = None):
    extra = extra or {}
    log_record = json.dumps({"message": message, **extra})
    await asyncio.to_thread(logger.log, level, log_record)


class LoggingMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, slow_request_threshold: float = 1.0):
        super().__init__(app)
        self.slow_request_threshold = slow_request_threshold

    async def dispatch(self, request: Request, call_next):
        request_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))
        start_time = time.perf_counter()

        try:
            response: Response = await call_next(request)
        except Exception as exc:
            await log_async(
                logging.ERROR,
                f"{request.method} {request.url.path} → EXCEPTION",
                extra={
                    "request_id": request_id,
                    "method": request.method,
                    "path": request.url.path,
                    "exception": repr(exc),
                },
            )
            raise

        duration_ms = round((time.perf_counter() - start_time) * 1000, 2)
        log_level = logging.WARNING if duration_ms >= self.slow_request_threshold * 1000 else logging.INFO

        await log_async(
            log_level,
            f"{request.method} {request.url.path} → {response.status_code}",
            extra={
                "request_id": request_id,
                "method": request.method,
                "path": request.url.path,
                "status_code": response.status_code,
                "duration_ms": duration_ms,
                "client_ip": request.client.host if request.client else None,
                "user_agent": request.headers.get("user-agent"),
            },
        )

        response.headers["X-Request-ID"] = request_id
        return response


def add_logging_middleware(app: FastAPI):
    app.add_middleware(LoggingMiddleware)
