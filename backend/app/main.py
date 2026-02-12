"""FastAPI application entry point with security hardening."""

import logging
import sys
from contextlib import asynccontextmanager

from fastapi import FastAPI, Depends, Request
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings, generate_api_key
from app.api.v1.router import api_router
from app.db.session import engine
from app.models.base import Base
from app.middleware import (
    RateLimitMiddleware,
    SecurityHeadersMiddleware,
    RequestLoggingMiddleware,
    InputSanitizationMiddleware,
    setup_logging,
)
from app.core.security import verify_api_key, optional_api_key
from app.core.exceptions import register_exception_handlers
from app.core.audit import audit_log, AuditAction


# Setup logging early
setup_logging()
logger = logging.getLogger(__name__)


def validate_startup_security() -> None:
    """
    Validate security configuration at startup.
    Exits with error in production if security requirements not met.
    """
    errors = settings.validate_production_settings()

    if errors:
        logger.error("=" * 60)
        logger.error("SECURITY CONFIGURATION ERRORS")
        logger.error("=" * 60)
        for error in errors:
            logger.error(f"  - {error}")
        logger.error("=" * 60)

        if settings.is_production():
            logger.critical("Refusing to start in production with insecure configuration!")
            sys.exit(1)
        else:
            logger.warning(
                "Running in development mode with insecure defaults. "
                "DO NOT use this configuration in production!"
            )

    # Log security status
    logger.info(f"Environment: {settings.app_env}")
    logger.info(f"API Key Required: {settings.api_key_required}")
    logger.info(f"Rate Limiting: {'enabled' if settings.rate_limit_enabled else 'disabled'}")
    logger.info(f"Debug Mode: {settings.debug}")

    # Generate example API key for development
    if not settings.is_production() and not settings.api_keys:
        example_key = generate_api_key()
        logger.info("-" * 60)
        logger.info("No API keys configured. To enable API key authentication:")
        logger.info(f"  1. Add to .env: API_KEYS={example_key}")
        logger.info(f"  2. Set: API_KEY_REQUIRED=true")
        logger.info("-" * 60)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler for startup and shutdown."""
    # Startup
    logger.info(f"Starting {settings.app_name}...")

    # Validate security configuration
    validate_startup_security()

    # Create database tables if they don't exist
    try:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        logger.info("Database connection established")
    except Exception as e:
        logger.error(f"Database connection failed: {e}")
        if settings.is_production():
            sys.exit(1)

    logger.info(f"{settings.app_name} started successfully")

    yield

    # Shutdown
    logger.info("Shutting down...")
    await engine.dispose()
    logger.info("Database connections closed")


# Create FastAPI application
app = FastAPI(
    title=settings.app_name,
    description="""
Micromobility navigation API for San Francisco with risk-aware routing.

## Authentication

This API uses API key authentication. Include your API key in the `X-API-Key` header:

```
X-API-Key: your-api-key-here
```

## Rate Limiting

- Unauthenticated requests: 100 requests per minute
- Authenticated requests: 300 requests per minute

Rate limit headers are included in all responses:
- `X-RateLimit-Limit`: Maximum requests allowed
- `X-RateLimit-Remaining`: Requests remaining in current window
- `X-RateLimit-Reset`: Unix timestamp when the limit resets

## Error Responses

All errors follow a consistent format:
```json
{
  "error": {
    "code": "ERROR_CODE",
    "message": "Human-readable message",
    "request_id": "abc123"
  }
}
```
    """,
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs" if not settings.is_production() else None,
    redoc_url="/redoc" if not settings.is_production() else None,
    openapi_url="/openapi.json" if not settings.is_production() else None,
)

# ============================================================================
# Register Exception Handlers (before middleware)
# ============================================================================
register_exception_handlers(app)

# ============================================================================
# Middleware Stack (order matters - first added = last executed)
# ============================================================================

# 1. Request logging (outermost - captures everything)
app.add_middleware(RequestLoggingMiddleware)

# 2. Input sanitization (early detection of malicious input)
app.add_middleware(InputSanitizationMiddleware)

# 3. Security headers
app.add_middleware(SecurityHeadersMiddleware)

# 4. Rate limiting
app.add_middleware(RateLimitMiddleware, use_redis=bool(settings.redis_url))

# 5. CORS (innermost for preflight handling)
# Production-hardened CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=settings.cors_allow_methods,  # Restricted, not ["*"]
    allow_headers=settings.cors_allow_headers,  # Restricted, not ["*"]
    expose_headers=[
        "X-Request-ID",
        "X-RateLimit-Limit",
        "X-RateLimit-Remaining",
        "X-RateLimit-Reset",
    ],
    max_age=600,  # Cache preflight for 10 minutes
)


# ============================================================================
# API Routes
# ============================================================================

# Include API router with optional authentication
# Individual endpoints can require authentication using Depends(verify_api_key)
app.include_router(api_router, prefix="/api/v1")


# ============================================================================
# Health and Root Endpoints (no authentication required)
# ============================================================================

@app.get("/health", tags=["Health"])
async def health_check():
    """
    Basic health check endpoint.
    Returns service status without requiring authentication.
    """
    return {
        "status": "healthy",
        "service": settings.app_name,
        "environment": settings.app_env,
    }


@app.get("/", tags=["Root"])
async def root():
    """
    Root endpoint with API information.
    """
    response = {
        "name": settings.app_name,
        "version": "1.0.0",
        "health": "/health",
    }

    # Only include docs links in non-production
    if not settings.is_production():
        response["docs"] = "/docs"
        response["redoc"] = "/redoc"

    return response


# ============================================================================
# Admin Endpoints (require authentication + audit logging)
# ============================================================================

def get_client_ip(request: Request) -> str:
    """Extract client IP from request."""
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()
    if request.client:
        return request.client.host
    return "unknown"


@app.get("/admin/config", tags=["Admin"], include_in_schema=False)
async def get_config(
    request: Request,
    api_key: str = Depends(verify_api_key)
):
    """
    Get non-sensitive configuration info (requires API key).
    """
    request_id = getattr(request.state, "request_id", "unknown")

    # Audit log the access
    audit_log.log_admin_action(
        AuditAction.ADMIN_CONFIG_VIEW,
        request_id=request_id,
        client_ip=get_client_ip(request),
        api_key=api_key,
    )

    return {
        "environment": settings.app_env,
        "rate_limit_enabled": settings.rate_limit_enabled,
        "rate_limit_requests": settings.rate_limit_requests,
        "rate_limit_window_seconds": settings.rate_limit_window_seconds,
        "cors_origins": settings.cors_origins,
        "debug": settings.debug,
    }


@app.post("/admin/generate-key", tags=["Admin"], include_in_schema=False)
async def generate_new_api_key(
    request: Request,
    api_key: str = Depends(verify_api_key)
):
    """
    Generate a new API key (requires existing API key).
    Note: This only generates the key - it must be manually added to config.
    """
    request_id = getattr(request.state, "request_id", "unknown")
    new_key = generate_api_key()

    # Audit log the key generation
    audit_log.log_admin_action(
        AuditAction.ADMIN_KEY_GENERATE,
        request_id=request_id,
        client_ip=get_client_ip(request),
        api_key=api_key,
        details={"new_key_prefix": new_key[:10] + "..."},
    )

    return {
        "key": new_key,
        "note": "Add this key to API_KEYS environment variable to activate"
    }


@app.get("/admin/audit", tags=["Admin"], include_in_schema=False)
async def get_audit_info(
    request: Request,
    api_key: str = Depends(verify_api_key)
):
    """
    Get audit logging status (requires API key).
    """
    request_id = getattr(request.state, "request_id", "unknown")

    audit_log.log_admin_action(
        AuditAction.ADMIN_ACCESS,
        request_id=request_id,
        client_ip=get_client_ip(request),
        api_key=api_key,
        details={"endpoint": "/admin/audit"},
    )

    return {
        "audit_logging": "enabled",
        "log_level": settings.log_level,
        "request_logging": settings.log_requests,
        "note": "Audit logs are written to application logs",
    }
