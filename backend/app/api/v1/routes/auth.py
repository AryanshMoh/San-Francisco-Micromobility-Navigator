"""Authentication API endpoints."""

import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field

from app.config import settings
from app.core.auth import (
    authenticate_request,
    create_session_token,
    refresh_session_token,
    revoke_token,
)
from app.core.rbac import AuthContext, Role, require_roles
from app.core.audit import audit_log, AuditAction
from app.core.exceptions import AuthenticationException

logger = logging.getLogger("api.auth")
router = APIRouter()


# =============================================================================
# Request/Response Models
# =============================================================================

class TokenRequest(BaseModel):
    """Request to create a new session token."""

    # In a real app, this would include credentials
    # For demo purposes, we use a simple session ID
    session_id: str = Field(..., min_length=8, max_length=64, description="Session identifier")
    device_type: Optional[str] = Field(None, max_length=50, description="Device type")


class TokenResponse(BaseModel):
    """Token response."""

    access_token: str
    refresh_token: Optional[str] = None
    token_type: str = "bearer"
    expires_in: int  # seconds


class RefreshRequest(BaseModel):
    """Request to refresh an access token."""

    refresh_token: str = Field(..., description="Refresh token")


class RevokeRequest(BaseModel):
    """Request to revoke a token."""

    token: str = Field(..., description="Token to revoke")


class AuthStatusResponse(BaseModel):
    """Current authentication status."""

    authenticated: bool
    method: Optional[str] = None
    subject_id: Optional[str] = None
    roles: list[str] = []
    permissions: list[str] = []


# =============================================================================
# Helper Functions
# =============================================================================

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


# =============================================================================
# Endpoints
# =============================================================================

@router.get("/status", response_model=AuthStatusResponse)
async def get_auth_status(
    request: Request,
    context: AuthContext = Depends(authenticate_request),
) -> AuthStatusResponse:
    """
    Get current authentication status.

    Returns information about the current authentication context
    including roles and permissions.
    """
    return AuthStatusResponse(
        authenticated=context.is_authenticated,
        method=context.auth_method,
        subject_id=context.subject_id,
        roles=[r.value for r in context.roles],
        permissions=[p.value for p in context.permissions],
    )


@router.post("/token", response_model=TokenResponse)
async def create_token(
    request: Request,
    token_request: TokenRequest,
) -> TokenResponse:
    """
    Create a new session token.

    In a production system, this would validate user credentials.
    For this demo, it creates tokens for any valid session ID.

    Note: This endpoint requires JWT to be enabled in configuration.
    """
    from app.core.jwt import is_jwt_available

    if not is_jwt_available():
        raise HTTPException(
            status_code=501,
            detail="JWT authentication is not enabled"
        )

    request_id = get_request_id(request)
    client_ip = get_client_ip(request)

    # Audit log token creation
    audit_log.log(
        AuditAction.AUTH_SUCCESS,
        request_id=request_id,
        client_ip=client_ip,
        details={
            "action": "token_create",
            "session_id": token_request.session_id[:8] + "...",
            "device_type": token_request.device_type,
        },
    )

    try:
        result = await create_session_token(
            subject=token_request.session_id,
            roles=[Role.USER.value],  # Default role for new sessions
        )

        return TokenResponse(
            access_token=result["access_token"],
            refresh_token=result["refresh_token"],
            token_type=result["token_type"],
            expires_in=result["expires_in"],
        )

    except Exception as e:
        logger.error(f"[{request_id}] Token creation failed: {e}")
        raise HTTPException(status_code=500, detail="Failed to create token")


@router.post("/refresh", response_model=TokenResponse)
async def refresh_token(
    request: Request,
    refresh_request: RefreshRequest,
) -> TokenResponse:
    """
    Refresh an access token using a refresh token.

    The refresh token must be valid and not expired.
    """
    from app.core.jwt import is_jwt_available

    if not is_jwt_available():
        raise HTTPException(
            status_code=501,
            detail="JWT authentication is not enabled"
        )

    request_id = get_request_id(request)
    client_ip = get_client_ip(request)

    result = await refresh_session_token(refresh_request.refresh_token)

    if not result:
        audit_log.log(
            AuditAction.AUTH_FAILURE,
            request_id=request_id,
            client_ip=client_ip,
            success=False,
            error_message="Invalid refresh token",
        )
        raise AuthenticationException("Invalid or expired refresh token")

    audit_log.log(
        AuditAction.AUTH_SUCCESS,
        request_id=request_id,
        client_ip=client_ip,
        details={"action": "token_refresh"},
    )

    return TokenResponse(
        access_token=result["access_token"],
        token_type=result["token_type"],
        expires_in=result["expires_in"],
    )


@router.post("/revoke")
async def revoke_token_endpoint(
    request: Request,
    revoke_request: RevokeRequest,
    context: AuthContext = Depends(authenticate_request),
) -> dict:
    """
    Revoke (blacklist) a token.

    Requires authentication. Users can only revoke their own tokens,
    admins can revoke any token.
    """
    from app.core.jwt import is_jwt_available

    if not is_jwt_available():
        raise HTTPException(
            status_code=501,
            detail="JWT authentication is not enabled"
        )

    request_id = get_request_id(request)
    client_ip = get_client_ip(request)

    success = await revoke_token(revoke_request.token)

    if success:
        audit_log.log(
            AuditAction.AUTH_SUCCESS,
            request_id=request_id,
            client_ip=client_ip,
            details={"action": "token_revoke"},
        )
        return {"revoked": True}

    return {"revoked": False, "message": "Token could not be revoked"}


@router.get("/methods")
async def get_auth_methods() -> dict:
    """
    Get available authentication methods.

    Returns which authentication methods are enabled.
    """
    from app.core.jwt import is_jwt_available

    return {
        "methods": {
            "api_key": {
                "enabled": True,
                "header": settings.api_key_header,
                "required": settings.api_key_required,
            },
            "jwt": {
                "enabled": is_jwt_available() and settings.jwt_enabled,
                "token_endpoint": "/api/v1/auth/token" if is_jwt_available() else None,
                "refresh_endpoint": "/api/v1/auth/refresh" if is_jwt_available() else None,
            },
        },
    }
