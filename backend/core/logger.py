import logging
import time
import uuid

import structlog
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response

logger = structlog.get_logger()


def configure_logging(log_level: str = "INFO", environment: str = "PROD") -> None:
    level = getattr(logging, log_level.upper(), logging.INFO)

    shared_processors = [
        structlog.contextvars.merge_contextvars,
        structlog.stdlib.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.ExceptionRenderer(),
    ]

    renderer = (
        structlog.dev.ConsoleRenderer(colors=True)
        if environment == "DEV"
        else structlog.processors.JSONRenderer()
    )

    structlog.configure(
        processors=shared_processors + [renderer],  # type: ignore[arg-type]
        wrapper_class=structlog.make_filtering_bound_logger(level),
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(),
        cache_logger_on_first_use=True,
    )

    logging.basicConfig(format="%(message)s", level=level, force=True)


class StructuredLoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next) -> Response:
        correlation_id = request.headers.get("X-Correlation-ID", str(uuid.uuid4()))

        structlog.contextvars.clear_contextvars()
        structlog.contextvars.bind_contextvars(
            correlation_id=correlation_id,
            method=request.method,
            path=request.url.path,
        )

        start_time = time.perf_counter()
        try:
            response = await call_next(request)
        except Exception:
            logger.exception("request_failed")
            raise

        duration_ms = round((time.perf_counter() - start_time) * 1000, 2)
        logger.info(
            "request_processed",
            status_code=response.status_code,
            duration_ms=duration_ms,
        )

        response.headers["X-Correlation-ID"] = correlation_id
        return response
