"""API v1 router aggregation."""

from fastapi import APIRouter

from app.api.v1.routes import routing, risk_zones, reports, health

api_router = APIRouter()

api_router.include_router(health.router, prefix="/health", tags=["Health"])
api_router.include_router(routing.router, prefix="/routes", tags=["Routing"])
api_router.include_router(risk_zones.router, prefix="/risk-zones", tags=["Risk Zones"])
api_router.include_router(reports.router, prefix="/reports", tags=["Reporting"])
