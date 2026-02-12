"""Centralized exception handling with sanitized error responses."""

import logging
import traceback
from typing import Any, Dict, Optional
from uuid import uuid4

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import ValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.config import settings

logger = logging.getLogger("api.errors")


# =============================================================================
# Custom Exception Classes
# =============================================================================

class APIException(Exception):
    """Base exception for API errors with safe messages."""

    def __init__(
        self,
        status_code: int = 500,
        detail: str = "An error occurred",
        error_code: Optional[str] = None,
        internal_message: Optional[str] = None,
    ):
        self.status_code = status_code
        self.detail = detail  # Safe message for client
        self.error_code = error_code or "INTERNAL_ERROR"
        self.internal_message = internal_message  # Full message for logs
        super().__init__(self.detail)


class ValidationException(APIException):
    """Validation error with safe field information."""

    def __init__(self, detail: str, field: Optional[str] = None):
        super().__init__(
            status_code=422,
            detail=detail,
            error_code="VALIDATION_ERROR",
        )
        self.field = field


class AuthenticationException(APIException):
    """Authentication failure."""

    def __init__(self, detail: str = "Authentication required"):
        super().__init__(
            status_code=401,
            detail=detail,
            error_code="AUTHENTICATION_REQUIRED",
        )


class AuthorizationException(APIException):
    """Authorization/permission failure."""

    def __init__(self, detail: str = "Permission denied"):
        super().__init__(
            status_code=403,
            detail=detail,
            error_code="PERMISSION_DENIED",
        )


class ResourceNotFoundException(APIException):
    """Resource not found."""

    def __init__(self, resource: str = "Resource", resource_id: Optional[str] = None):
        detail = f"{resource} not found"
        super().__init__(
            status_code=404,
            detail=detail,
            error_code="NOT_FOUND",
        )


class RateLimitException(APIException):
    """Rate limit exceeded."""

    def __init__(self, retry_after: int = 60):
        super().__init__(
            status_code=429,
            detail="Rate limit exceeded. Please try again later.",
            error_code="RATE_LIMIT_EXCEEDED",
        )
        self.retry_after = retry_after


class ServiceUnavailableException(APIException):
    """External service unavailable."""

    def __init__(self, service: str = "Service"):
        super().__init__(
            status_code=503,
            detail="Service temporarily unavailable. Please try again later.",
            error_code="SERVICE_UNAVAILABLE",
            internal_message=f"{service} is unavailable",
        )


class RoutingException(APIException):
    """Routing-specific errors."""

    def __init__(self, detail: str = "Unable to calculate route"):
        super().__init__(
            status_code=422,
            detail=detail,
            error_code="ROUTING_ERROR",
        )


# =============================================================================
# Error Response Formatting
# =============================================================================

def create_error_response(
    status_code: int,
    error_code: str,
    message: str,
    request_id: Optional[str] = None,
    details: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Create a standardized error response."""
    response = {
        "error": {
            "code": error_code,
            "message": message,
        }
    }

    if request_id:
        response["error"]["request_id"] = request_id

    if details and not settings.is_production():
        # Only include details in non-production
        response["error"]["details"] = details

    return response


def sanitize_error_message(message: str) -> str:
    """
    Sanitize error message to remove sensitive information.

    Removes:
    - File paths
    - SQL queries
    - Stack traces
    - Internal implementation details
    """
    # Patterns that indicate internal details
    sensitive_patterns = [
        "/app/",
        "/usr/",
        "/home/",
        "Traceback",
        "File \"",
        "SELECT ",
        "INSERT ",
        "UPDATE ",
        "DELETE ",
        "postgresql",
        "asyncpg",
        "sqlalchemy",
        "password",
        "secret",
        "token",
        "api_key",
    ]

    message_lower = message.lower()
    for pattern in sensitive_patterns:
        if pattern.lower() in message_lower:
            return "An internal error occurred. Please try again later."

    # Limit message length
    if len(message) > 200:
        return message[:200] + "..."

    return message


# =============================================================================
# Exception Handlers
# =============================================================================

def get_request_id(request: Request) -> str:
    """Get request ID from request state or generate new one."""
    if hasattr(request.state, "request_id"):
        return request.state.request_id
    return str(uuid4())[:8]


async def api_exception_handler(request: Request, exc: APIException) -> JSONResponse:
    """Handle custom API exceptions."""
    request_id = get_request_id(request)

    # Log the error
    log_message = f"[{request_id}] {exc.error_code}: {exc.detail}"
    if exc.internal_message:
        log_message += f" | Internal: {exc.internal_message}"

    if exc.status_code >= 500:
        logger.error(log_message)
    else:
        logger.warning(log_message)

    response = create_error_response(
        status_code=exc.status_code,
        error_code=exc.error_code,
        message=exc.detail,
        request_id=request_id,
    )

    headers = {}
    if isinstance(exc, RateLimitException):
        headers["Retry-After"] = str(exc.retry_after)

    return JSONResponse(
        status_code=exc.status_code,
        content=response,
        headers=headers,
    )


async def http_exception_handler(
    request: Request, exc: StarletteHTTPException
) -> JSONResponse:
    """Handle standard HTTP exceptions with sanitization."""
    request_id = get_request_id(request)

    # Map status codes to error codes
    error_code_map = {
        400: "BAD_REQUEST",
        401: "UNAUTHORIZED",
        403: "FORBIDDEN",
        404: "NOT_FOUND",
        405: "METHOD_NOT_ALLOWED",
        422: "VALIDATION_ERROR",
        429: "RATE_LIMITED",
        500: "INTERNAL_ERROR",
        502: "BAD_GATEWAY",
        503: "SERVICE_UNAVAILABLE",
    }

    error_code = error_code_map.get(exc.status_code, "ERROR")

    # Sanitize the detail message
    detail = exc.detail if isinstance(exc.detail, str) else str(exc.detail)
    if exc.status_code >= 500:
        detail = sanitize_error_message(detail)

    # Log the error
    if exc.status_code >= 500:
        logger.error(f"[{request_id}] HTTP {exc.status_code}: {exc.detail}")
    else:
        logger.info(f"[{request_id}] HTTP {exc.status_code}: {detail}")

    response = create_error_response(
        status_code=exc.status_code,
        error_code=error_code,
        message=detail,
        request_id=request_id,
    )

    return JSONResponse(status_code=exc.status_code, content=response)


async def validation_exception_handler(
    request: Request, exc: RequestValidationError
) -> JSONResponse:
    """Handle Pydantic validation errors with safe messages."""
    request_id = get_request_id(request)

    # Extract field errors without exposing internal details
    field_errors = []
    for error in exc.errors():
        field = ".".join(str(loc) for loc in error["loc"] if loc != "body")
        msg = error["msg"]

        # Sanitize the message
        if "value_error" in str(error.get("type", "")):
            msg = "Invalid value provided"

        field_errors.append({
            "field": field,
            "message": msg,
        })

    logger.info(f"[{request_id}] Validation error: {len(field_errors)} field(s)")

    response = create_error_response(
        status_code=422,
        error_code="VALIDATION_ERROR",
        message="Invalid request data",
        request_id=request_id,
        details={"fields": field_errors} if not settings.is_production() else None,
    )

    return JSONResponse(status_code=422, content=response)


async def generic_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Handle unexpected exceptions with full sanitization."""
    request_id = get_request_id(request)

    # Log full error details internally
    logger.error(
        f"[{request_id}] Unhandled exception: {type(exc).__name__}: {str(exc)}"
    )
    if settings.debug:
        logger.error(traceback.format_exc())

    # Return generic message to client
    response = create_error_response(
        status_code=500,
        error_code="INTERNAL_ERROR",
        message="An unexpected error occurred. Please try again later.",
        request_id=request_id,
    )

    return JSONResponse(status_code=500, content=response)


# =============================================================================
# Register Exception Handlers
# =============================================================================

def register_exception_handlers(app: FastAPI) -> None:
    """Register all exception handlers with the FastAPI app."""
    app.add_exception_handler(APIException, api_exception_handler)
    app.add_exception_handler(StarletteHTTPException, http_exception_handler)
    app.add_exception_handler(RequestValidationError, validation_exception_handler)
    app.add_exception_handler(Exception, generic_exception_handler)
