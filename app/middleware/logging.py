from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
import logging

logger = logging.getLogger("uvicorn.access")


class LoggingMiddleware(BaseHTTPMiddleware):
    # TODO Complete This
    pass


def add_logging_middleware(app):
    app.add_middleware(LoggingMiddleware)
