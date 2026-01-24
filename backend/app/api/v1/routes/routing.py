"""Routing API endpoints."""

from typing import List
from uuid import UUID

from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.schemas.routing import (
    RouteRequest,
    RouteResponse,
    RouteComparison,
)
from app.services.routing.engine import routing_engine

router = APIRouter()


@router.post("/calculate", response_model=RouteResponse)
async def calculate_route(
    request: RouteRequest,
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
    try:
        route = await routing_engine.calculate_route(request)
        return route
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Routing failed: {str(e)}")


@router.post("/alternatives")
async def get_alternative_routes(
    request: RouteRequest,
    db: AsyncSession = Depends(get_db),
) -> dict:
    """
    Get alternative routes with different trade-offs.

    Returns up to 3 routes:
    - Safest (prioritizes bike lanes, avoids risks)
    - Fastest (shortest time)
    - Balanced (compromise between safety and speed)
    """
    try:
        routes = await routing_engine.calculate_alternatives(request)

        if not routes:
            raise HTTPException(status_code=422, detail="No routes found")

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
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Routing failed: {str(e)}")


@router.get("/{route_id}/elevation")
async def get_route_elevation(
    route_id: UUID,
    sample_points: int = 100,
) -> dict:
    """
    Get elevation profile for a previously calculated route.

    Returns elevation data points along the route for visualization.
    """
    # TODO: Implement elevation profile retrieval
    # This would query cached route and return elevation data

    return {
        "route_id": str(route_id),
        "sample_points": sample_points,
        "elevation_data": [],  # Placeholder
        "message": "Elevation profile not yet implemented",
    }
