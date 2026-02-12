"""Request logging middleware for audit trail and debugging."""

import logging
import time
import uuid
from typing import Callable

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

from app.config import settings
from app.core.security import mask_api_key


# Configure logger
logger = logging.getLogger("api.requests")


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """
    Logs all incoming requests and outgoing responses.

    Features:
    - Unique request ID for tracing
    - Request duration tracking
    - Sensitive data masking (API keys, passwords)
    - Structured logging format
    - Configurable log levels
    """

    # Headers that should be masked in logs
    SENSITIVE_HEADERS = {
        "authorization",
        "x-api-key",
        "cookie",
        "set-cookie",
    }

    # Paths with reduced logging (health checks, etc.)
    QUIET_PATHS = {"/health", "/health/ready", "/health/db"}

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Skip logging if disabled
        if not settings.log_requests:
            return await call_next(request)

        # Generate unique request ID
        request_id = str(uuid.uuid4())[:8]

        # Add request ID to request state for use in handlers
        request.state.request_id = request_id

        # Record start time
        start_time = time.time()

        # Extract request info
        client_ip = self._get_client_ip(request)
        method = request.method
        path = request.url.path
        query = str(request.url.query) if request.url.query else ""

        # Determine log level based on path
        is_quiet_path = path in self.QUIET_PATHS

        # Log incoming request (debug level for quiet paths)
        if not is_quiet_path:
            logger.info(
                f"[{request_id}] --> {method} {path}"
                f"{('?' + query) if query else ''} "
                f"from {client_ip}"
            )

        # Process request
        try:
            response = await call_next(request)
            status_code = response.status_code
            error = None
        except Exception as e:
            status_code = 500
            error = str(e)
            raise
        finally:
            # Calculate duration
            duration_ms = (time.time() - start_time) * 1000

            # Add request ID to response headers
            if 'response' in dir() and response:
                response.headers["X-Request-ID"] = request_id

            # Log response
            log_message = (
                f"[{request_id}] <-- {status_code} "
                f"{method} {path} "
                f"({duration_ms:.2f}ms)"
            )

            if error:
                log_message += f" ERROR: {error}"

            # Choose log level based on status code
            if status_code >= 500:
                logger.error(log_message)
            elif status_code >= 400:
                logger.warning(log_message)
            elif not is_quiet_path:
                logger.info(log_message)
            else:
                logger.debug(log_message)

        return response

    def _get_client_ip(self, request: Request) -> str:
        """Extract client IP from request, handling proxies."""
        # Check for forwarded header (from reverse proxy)
        forwarded = request.headers.get("X-Forwarded-For")
        if forwarded:
            return forwarded.split(",")[0].strip()

        # Check for real IP header (from some proxies)
        real_ip = request.headers.get("X-Real-IP")
        if real_ip:
            return real_ip

        # Fall back to direct connection
        if request.client:
            return request.client.host

        return "unknown"

    def _mask_headers(self, headers: dict) -> dict:
        """Mask sensitive header values for logging."""
        masked = {}
        for key, value in headers.items():
            if key.lower() in self.SENSITIVE_HEADERS:
                if key.lower() == "x-api-key":
                    masked[key] = mask_api_key(value)
                else:
                    masked[key] = "****"
            else:
                masked[key] = value
        return masked


def setup_logging():
    """Configure logging for the application."""
    log_level = getattr(logging, settings.log_level.upper(), logging.INFO)

    # Configure root logger
    logging.basicConfig(
        level=log_level,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )

    # Set specific logger levels
    logging.getLogger("api.requests").setLevel(log_level)
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)

    # Reduce noise from third-party libraries
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    logging.getLogger("asyncio").setLevel(logging.WARNING)
