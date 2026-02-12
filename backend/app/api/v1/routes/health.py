"""Health check endpoints."""

import httpx
from fastapi import APIRouter, Depends, Response
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.config import settings

router = APIRouter()


@router.get("")
async def health_check():
    """Basic health check - always returns 200 if app is running."""
    return {"status": "healthy"}


@router.get("/db")
async def database_health(db: AsyncSession = Depends(get_db), response: Response = None):
    """Check database connection health.

    Returns HTTP 503 if database is unavailable.
    """
    try:
        await db.execute(text("SELECT 1"))
        return {"status": "healthy", "database": "connected"}
    except Exception as e:
        if response:
            response.status_code = 503
        return {"status": "unhealthy", "database": "disconnected", "error": str(e)}


@router.get("/ready")
async def readiness_check(db: AsyncSession = Depends(get_db), response: Response = None):
    """Readiness check for all critical services.

    Returns HTTP 503 if any critical service is unavailable.
    """
    checks = {
        "database": False,
        "valhalla": False,
        "redis": False,
    }
    errors = {}

    # Check database
    try:
        await db.execute(text("SELECT 1"))
        checks["database"] = True
    except Exception as e:
        errors["database"] = str(e)

    # Check Valhalla routing engine
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            valhalla_response = await client.get(f"{settings.valhalla_url}/status")
            checks["valhalla"] = valhalla_response.status_code == 200
    except Exception as e:
        errors["valhalla"] = str(e)

    # Check Redis
    try:
        import redis.asyncio as redis
        r = redis.from_url(settings.redis_url)
        await r.ping()
        await r.close()
        checks["redis"] = True
    except Exception as e:
        errors["redis"] = str(e)

    all_healthy = all(checks.values())

    # Return 503 if not ready
    if not all_healthy and response:
        response.status_code = 503

    result = {
        "status": "ready" if all_healthy else "not_ready",
        "checks": checks,
    }

    if errors:
        result["errors"] = errors

    return result
