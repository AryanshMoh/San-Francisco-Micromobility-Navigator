"""Security headers middleware for defense-in-depth protection."""

from typing import Callable

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

from app.config import settings


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """
    Adds security headers to all responses.

    Headers added:
    - X-Content-Type-Options: Prevents MIME type sniffing
    - X-Frame-Options: Prevents clickjacking
    - X-XSS-Protection: Legacy XSS protection (for older browsers)
    - Referrer-Policy: Controls referrer information
    - Content-Security-Policy: Controls resource loading
    - Strict-Transport-Security: Enforces HTTPS (in production)
    - Permissions-Policy: Controls browser features
    - Cache-Control: Prevents caching of sensitive data
    """

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        response = await call_next(request)

        # Prevent MIME type sniffing
        response.headers["X-Content-Type-Options"] = "nosniff"

        # Prevent clickjacking
        response.headers["X-Frame-Options"] = "DENY"

        # Legacy XSS protection (modern browsers use CSP)
        response.headers["X-XSS-Protection"] = "1; mode=block"

        # Control referrer information
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"

        # Content Security Policy
        # Use permissive CSP for documentation pages, strict for API
        if self._is_docs_path(request):
            response.headers["Content-Security-Policy"] = (
                "default-src 'self'; "
                "script-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net; "
                "style-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net; "
                "img-src 'self' data: https://fastapi.tiangolo.com; "
                "font-src 'self' https://cdn.jsdelivr.net; "
                "connect-src 'self' https://cdn.jsdelivr.net; "
                "frame-ancestors 'none'"
            )
        else:
            response.headers["Content-Security-Policy"] = (
                "default-src 'none'; "
                "frame-ancestors 'none'"
            )

        # HTTP Strict Transport Security (only in production)
        if settings.is_production():
            response.headers["Strict-Transport-Security"] = (
                "max-age=31536000; includeSubDomains; preload"
            )

        # Disable various browser features not needed by API
        response.headers["Permissions-Policy"] = (
            "accelerometer=(), "
            "camera=(), "
            "geolocation=(), "
            "gyroscope=(), "
            "magnetometer=(), "
            "microphone=(), "
            "payment=(), "
            "usb=()"
        )

        # Prevent caching of API responses with sensitive data
        if self._should_prevent_caching(request):
            response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, private"
            response.headers["Pragma"] = "no-cache"
            response.headers["Expires"] = "0"

        return response

    def _is_docs_path(self, request: Request) -> bool:
        """Check if request is for documentation pages."""
        docs_paths = {"/docs", "/redoc", "/openapi.json"}
        return request.url.path in docs_paths

    def _should_prevent_caching(self, request: Request) -> bool:
        """Determine if response should not be cached."""
        # Don't cache authenticated requests
        if request.headers.get(settings.api_key_header):
            return True

        # Don't cache POST/PUT/DELETE responses
        if request.method in ("POST", "PUT", "DELETE", "PATCH"):
            return True

        # Allow caching for certain safe endpoints
        safe_paths = {"/health", "/docs", "/redoc", "/openapi.json"}
        if request.url.path in safe_paths:
            return False

        # Default: prevent caching
        return True
