"""Routing API endpoints with security hardening."""

from typing import List
from uuid import UUID

from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession
import httpx

from app.db.session import get_db
from app.schemas.routing import (
    RouteRequest,
    RouteResponse,
    RouteComparison,
)
from app.services.routing.engine import routing_engine
from app.core.exceptions import RoutingException, ServiceUnavailableException
from app.core.audit import audit_log, AuditAction
from app.services.risk_zone_service import RiskZoneServiceError

router = APIRouter()


def get_request_id(request: Request) -> str:
    """Get request ID from request state."""
    return getattr(request.state, "request_id", "unknown")


def get_client_ip(request: Request) -> str:
    """Extract client IP from request."""
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()
    if request.client:
        return request.client.host
    return "unknown"


@router.post("/calculate", response_model=RouteResponse)
async def calculate_route(
    route_request: RouteRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> RouteResponse:
    """
    Calculate the optimal route between two points.

    Takes into account:
    - Bike lane availability and type
    - Elevation/hills
    - User preferences (safest, fastest, balanced)
    - Known risk zones
    """
    request_id = get_request_id(request)

    # Audit log the route calculation request
    audit_log.log(
        AuditAction.ROUTE_CALCULATE,
        request_id=request_id,
        client_ip=get_client_ip(request),
        details={
            "origin": f"{route_request.origin.latitude},{route_request.origin.longitude}",
            "destination": f"{route_request.destination.latitude},{route_request.destination.longitude}",
            "profile": route_request.preferences.profile if route_request.preferences else "default",
        },
    )

    try:
        route = await routing_engine.calculate_route(route_request)
        return route
    except ValueError as e:
        # Validation errors - safe to return message
        raise RoutingException(detail=str(e))
    except (ConnectionError, httpx.ConnectError, httpx.TimeoutException) as e:
        # External service unavailable - return 503
        audit_log.log(
            AuditAction.ROUTE_CALCULATE,
            request_id=request_id,
            client_ip=get_client_ip(request),
            success=False,
            error_message=f"Valhalla unavailable: {e}",
        )
        raise ServiceUnavailableException(service="Routing engine")
    except httpx.HTTPStatusError as e:
        # Valhalla returned an error response
        audit_log.log(
            AuditAction.ROUTE_CALCULATE,
            request_id=request_id,
            client_ip=get_client_ip(request),
            success=False,
            error_message=f"Valhalla error: {e.response.status_code}",
        )
        raise ServiceUnavailableException(service="Routing engine")
    except RiskZoneServiceError as e:
        # Risk zone data unavailable - safety-critical failure
        audit_log.log(
            AuditAction.ROUTE_CALCULATE,
            request_id=request_id,
            client_ip=get_client_ip(request),
            success=False,
            error_message=f"Risk zone service failure: {e}",
        )
        raise ServiceUnavailableException(service="Risk zone service")
    except httpx.HTTPError as e:
        # Any other httpx errors (network issues, etc.) are service failures
        audit_log.log(
            AuditAction.ROUTE_CALCULATE,
            request_id=request_id,
            client_ip=get_client_ip(request),
            success=False,
            error_message=f"HTTP error: {e}",
        )
        raise ServiceUnavailableException(service="Routing engine")
    except Exception as e:
        # Log the full error internally, return generic 500 for unexpected errors
        audit_log.log(
            AuditAction.ROUTE_CALCULATE,
            request_id=request_id,
            client_ip=get_client_ip(request),
            success=False,
            error_message=str(e),
        )
        # Use 500 for unexpected errors, not 422 (which implies client error)
        raise ServiceUnavailableException(service="Routing")


@router.post("/alternatives")
async def get_alternative_routes(
    route_request: RouteRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> dict:
    """
    Get alternative routes with different trade-offs.

    Returns up to 3 routes:
    - Safest (prioritizes bike lanes, avoids risks)
    - Fastest (shortest time)
    - Balanced (compromise between safety and speed)
    """
    request_id = get_request_id(request)

    # Audit log the request
    audit_log.log(
        AuditAction.ROUTE_ALTERNATIVES,
        request_id=request_id,
        client_ip=get_client_ip(request),
        details={
            "origin": f"{route_request.origin.latitude},{route_request.origin.longitude}",
            "destination": f"{route_request.destination.latitude},{route_request.destination.longitude}",
        },
    )

    try:
        routes = await routing_engine.calculate_alternatives(route_request)

        if not routes:
            raise RoutingException(detail="No routes found between the specified locations")

        # Find indices for comparison
        fastest_idx = min(
            range(len(routes)), key=lambda i: routes[i].summary.duration_seconds
        )
        safest_idx = min(range(len(routes)), key=lambda i: routes[i].summary.risk_score)
        # Recommend balanced (middle) route
        recommended_idx = len(routes) // 2

        return {
            "routes": routes,
            "comparison": RouteComparison(
                fastest_index=fastest_idx,
                safest_index=safest_idx,
                recommended_index=recommended_idx,
            ),
        }
    except RoutingException:
        raise
    except ValueError as e:
        raise RoutingException(detail=str(e))
    except (ConnectionError, httpx.ConnectError, httpx.TimeoutException, httpx.HTTPStatusError, httpx.HTTPError):
        raise ServiceUnavailableException(service="Routing engine")
    except RiskZoneServiceError:
        raise ServiceUnavailableException(service="Risk zone service")
    except Exception as e:
        audit_log.log(
            AuditAction.ROUTE_ALTERNATIVES,
            request_id=request_id,
            client_ip=get_client_ip(request),
            success=False,
            error_message=str(e),
        )
        # Use 503 for unexpected errors, not 422 (which implies client error)
        raise ServiceUnavailableException(service="Routing")


@router.get("/{route_id}/elevation")
async def get_route_elevation(
    route_id: UUID,
    request: Request,
    sample_points: int = 100,
) -> dict:
    """
    Get elevation profile for a previously calculated route.

    Returns elevation data points along the route for visualization.
    """
    request_id = get_request_id(request)

    # Audit log the data access
    audit_log.log(
        AuditAction.DATA_READ,
        request_id=request_id,
        client_ip=get_client_ip(request),
        resource_type="route_elevation",
        resource_id=str(route_id),
    )

    # TODO: Implement elevation profile retrieval
    # This would query cached route and return elevation data

    return {
        "route_id": str(route_id),
        "sample_points": sample_points,
        "elevation_data": [],  # Placeholder
        "message": "Elevation profile not yet implemented",
    }
