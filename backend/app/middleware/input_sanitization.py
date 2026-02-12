"""Input sanitization middleware for defense-in-depth."""

import re
import logging
from typing import Callable, List, Pattern, Set

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse

from app.config import settings

logger = logging.getLogger("api.security")


class InputSanitizationMiddleware(BaseHTTPMiddleware):
    """
    Middleware for detecting and blocking malicious input patterns.

    Checks:
    - SQL injection patterns
    - XSS patterns
    - Path traversal attempts
    - Command injection patterns
    - Oversized payloads
    """

    # Maximum request body size (10MB)
    MAX_BODY_SIZE = 10 * 1024 * 1024

    # Maximum URL length
    MAX_URL_LENGTH = 2048

    # Maximum header value length
    MAX_HEADER_LENGTH = 8192

    # SQL injection patterns
    SQL_PATTERNS: List[Pattern] = [
        re.compile(r"(\b(SELECT|INSERT|UPDATE|DELETE|DROP|UNION|ALTER|CREATE|TRUNCATE)\b)", re.I),
        re.compile(r"(--|#|/\*|\*/)", re.I),
        re.compile(r"(\bOR\b\s+\d+\s*=\s*\d+)", re.I),
        re.compile(r"(\bAND\b\s+\d+\s*=\s*\d+)", re.I),
        re.compile(r"(;\s*\bDROP\b)", re.I),
        re.compile(r"(\'\s*\bOR\b\s*\')", re.I),
    ]

    # XSS patterns
    XSS_PATTERNS: List[Pattern] = [
        re.compile(r"<script[^>]*>", re.I),
        re.compile(r"javascript:", re.I),
        re.compile(r"on\w+\s*=", re.I),
        re.compile(r"<iframe", re.I),
        re.compile(r"<object", re.I),
        re.compile(r"<embed", re.I),
    ]

    # Path traversal patterns
    PATH_TRAVERSAL_PATTERNS: List[Pattern] = [
        re.compile(r"\.\.\/"),
        re.compile(r"\.\.\\"),
        re.compile(r"%2e%2e%2f", re.I),
        re.compile(r"%2e%2e/", re.I),
        re.compile(r"\.%2e/", re.I),
    ]

    # Command injection patterns
    COMMAND_PATTERNS: List[Pattern] = [
        re.compile(r"[;&|`$]"),
        re.compile(r"\$\("),
        re.compile(r"\$\{"),
    ]

    # Headers to check for malicious content
    HEADERS_TO_CHECK: Set[str] = {
        "user-agent",
        "referer",
        "x-forwarded-for",
        "x-real-ip",
    }

    # Paths exempt from certain checks (e.g., allow SQL keywords in search)
    RELAXED_PATHS: Set[str] = {
        "/docs",
        "/redoc",
        "/openapi.json",
    }

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Process request with input validation."""

        request_id = getattr(request.state, "request_id", "unknown")
        client_ip = self._get_client_ip(request)

        # Check URL length
        if len(str(request.url)) > self.MAX_URL_LENGTH:
            logger.warning(
                f"[{request_id}] Blocked: URL too long ({len(str(request.url))} chars) "
                f"from {client_ip}"
            )
            return self._blocked_response("URL too long", request_id)

        # Check for path traversal in URL
        if self._check_patterns(str(request.url.path), self.PATH_TRAVERSAL_PATTERNS):
            logger.warning(
                f"[{request_id}] Blocked: Path traversal attempt from {client_ip}: "
                f"{request.url.path}"
            )
            return self._blocked_response("Invalid request path", request_id)

        # Check query parameters
        for key, value in request.query_params.items():
            if self._is_malicious(value, request.url.path):
                logger.warning(
                    f"[{request_id}] Blocked: Malicious query param '{key}' "
                    f"from {client_ip}"
                )
                return self._blocked_response("Invalid request parameters", request_id)

        # Check relevant headers
        for header_name in self.HEADERS_TO_CHECK:
            header_value = request.headers.get(header_name, "")
            if len(header_value) > self.MAX_HEADER_LENGTH:
                logger.warning(
                    f"[{request_id}] Blocked: Header '{header_name}' too long "
                    f"from {client_ip}"
                )
                return self._blocked_response("Invalid request headers", request_id)

            # Check for XSS in headers
            if self._check_patterns(header_value, self.XSS_PATTERNS):
                logger.warning(
                    f"[{request_id}] Blocked: XSS in header '{header_name}' "
                    f"from {client_ip}"
                )
                return self._blocked_response("Invalid request headers", request_id)

        # Check Content-Length
        content_length = request.headers.get("content-length")
        if content_length:
            try:
                if int(content_length) > self.MAX_BODY_SIZE:
                    logger.warning(
                        f"[{request_id}] Blocked: Payload too large "
                        f"({content_length} bytes) from {client_ip}"
                    )
                    return self._blocked_response("Request body too large", request_id, 413)
            except ValueError:
                pass

        return await call_next(request)

    def _is_malicious(self, value: str, path: str) -> bool:
        """Check if a value contains malicious patterns."""
        if not value:
            return False

        # Skip relaxed paths
        if path in self.RELAXED_PATHS:
            return False

        # Check all pattern types
        pattern_checks = [
            (self.XSS_PATTERNS, "XSS"),
            (self.PATH_TRAVERSAL_PATTERNS, "Path Traversal"),
            (self.COMMAND_PATTERNS, "Command Injection"),
        ]

        # SQL checks only for certain contexts
        if not path.startswith("/api/v1/routes"):
            pattern_checks.append((self.SQL_PATTERNS, "SQL Injection"))

        for patterns, pattern_type in pattern_checks:
            if self._check_patterns(value, patterns):
                return True

        return False

    def _check_patterns(self, value: str, patterns: List[Pattern]) -> bool:
        """Check if value matches any of the patterns."""
        for pattern in patterns:
            if pattern.search(value):
                return True
        return False

    def _get_client_ip(self, request: Request) -> str:
        """Extract client IP from request."""
        forwarded = request.headers.get("X-Forwarded-For")
        if forwarded:
            return forwarded.split(",")[0].strip()
        if request.client:
            return request.client.host
        return "unknown"

    def _blocked_response(
        self,
        message: str,
        request_id: str,
        status_code: int = 400
    ) -> JSONResponse:
        """Create a blocked request response."""
        return JSONResponse(
            status_code=status_code,
            content={
                "error": {
                    "code": "INVALID_REQUEST",
                    "message": message,
                    "request_id": request_id,
                }
            }
        )
