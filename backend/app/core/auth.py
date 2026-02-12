"""Unified authentication module supporting API keys and JWT."""

import logging
from typing import Optional, Tuple

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import APIKeyHeader, HTTPBearer, HTTPAuthorizationCredentials

from app.config import settings
from app.core.security import api_key_validator, mask_api_key
from app.core.exceptions import AuthenticationException
from app.core.audit import audit_log, AuditAction, AuditSeverity
from app.core.rbac import AuthContext, Role, get_permissions_for_roles, get_auth_context

logger = logging.getLogger("api.auth")


# Security schemes
api_key_scheme = APIKeyHeader(name=settings.api_key_header, auto_error=False)
bearer_scheme = HTTPBearer(auto_error=False)


class AuthenticationResult:
    """Result of authentication attempt."""

    def __init__(
        self,
        success: bool,
        context: Optional[AuthContext] = None,
        error: Optional[str] = None,
        method: Optional[str] = None,
    ):
        self.success = success
        self.context = context
        self.error = error
        self.method = method


async def authenticate_request(
    request: Request,
    api_key: Optional[str] = Depends(api_key_scheme),
    bearer: Optional[HTTPAuthorizationCredentials] = Depends(bearer_scheme),
) -> AuthContext:
    """
    Authenticate request using available credentials.

    Priority:
    1. API Key (X-API-Key header)
    2. JWT Bearer token (Authorization: Bearer <token>)
    3. Public access (if allowed)

    Returns:
        AuthContext with authentication and authorization info
    """
    request_id = getattr(request.state, "request_id", "unknown")
    client_ip = _get_client_ip(request)

    # Try API key authentication
    if api_key:
        result = _authenticate_api_key(api_key, request_id, client_ip)
        if result.success:
            return result.context
        elif settings.api_key_required:
            # API key was provided but invalid, and keys are required
            audit_log.log_auth_failure(request_id, client_ip, result.error or "Invalid API key")
            raise AuthenticationException(result.error or "Invalid API key")

    # Try JWT authentication
    if bearer:
        result = await _authenticate_jwt(bearer.credentials, request_id, client_ip)
        if result.success:
            return result.context
        # JWT was provided but invalid
        audit_log.log_auth_failure(request_id, client_ip, result.error or "Invalid token")
        raise AuthenticationException(result.error or "Invalid token")

    # No credentials provided
    if settings.api_key_required:
        audit_log.log_auth_failure(request_id, client_ip, "No credentials provided")
        raise AuthenticationException("Authentication required")

    # Return public access context
    return AuthContext(
        is_authenticated=False,
        roles=[Role.PUBLIC],
        permissions=get_permissions_for_roles([Role.PUBLIC]),
        request_id=request_id,
        client_ip=client_ip,
    )


def _authenticate_api_key(
    api_key: str,
    request_id: str,
    client_ip: str,
) -> AuthenticationResult:
    """Authenticate using API key."""
    is_valid, error = api_key_validator.validate(api_key)

    if not is_valid:
        logger.warning(f"[{request_id}] API key auth failed from {client_ip}: {error}")
        return AuthenticationResult(
            success=False,
            error=error,
            method="api_key",
        )

    # Log successful auth
    audit_log.log_auth_success(request_id, client_ip, api_key)

    # Create context with admin role for API keys
    context = AuthContext(
        is_authenticated=True,
        auth_method="api_key",
        subject_id=mask_api_key(api_key),
        subject_type="service",
        roles=[Role.ADMIN],
        permissions=get_permissions_for_roles([Role.ADMIN]),
        request_id=request_id,
        client_ip=client_ip,
    )

    return AuthenticationResult(
        success=True,
        context=context,
        method="api_key",
    )


async def _authenticate_jwt(
    token: str,
    request_id: str,
    client_ip: str,
) -> AuthenticationResult:
    """Authenticate using JWT token."""
    try:
        from app.core.jwt import get_jwt_manager, is_jwt_available

        if not is_jwt_available():
            return AuthenticationResult(
                success=False,
                error="JWT authentication not available",
                method="jwt",
            )

        jwt_manager = get_jwt_manager()
        payload = jwt_manager.decode_token(token)

        if not payload:
            return AuthenticationResult(
                success=False,
                error="Invalid or expired token",
                method="jwt",
            )

        if payload.type != "access":
            return AuthenticationResult(
                success=False,
                error="Invalid token type",
                method="jwt",
            )

        # Convert role strings to Role enums
        roles = []
        for role_str in payload.roles:
            try:
                roles.append(Role(role_str))
            except ValueError:
                logger.warning(f"Unknown role in token: {role_str}")

        if not roles:
            roles = [Role.USER]

        # Log successful auth
        audit_log.log_auth_success(request_id, client_ip, f"jwt:{payload.sub[:8]}...")

        context = AuthContext(
            is_authenticated=True,
            auth_method="jwt",
            subject_id=payload.sub,
            subject_type="user",
            roles=roles,
            permissions=get_permissions_for_roles(roles),
            request_id=request_id,
            client_ip=client_ip,
        )

        return AuthenticationResult(
            success=True,
            context=context,
            method="jwt",
        )

    except Exception as e:
        logger.error(f"[{request_id}] JWT auth error: {e}")
        return AuthenticationResult(
            success=False,
            error="Authentication failed",
            method="jwt",
        )


def _get_client_ip(request: Request) -> str:
    """Extract client IP from request."""
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()
    if request.client:
        return request.client.host
    return "unknown"


# =============================================================================
# Convenience Dependencies
# =============================================================================

async def require_authentication(
    context: AuthContext = Depends(authenticate_request),
) -> AuthContext:
    """Require any valid authentication."""
    if not context.is_authenticated:
        raise AuthenticationException("Authentication required")
    return context


async def optional_authentication(
    request: Request,
    api_key: Optional[str] = Depends(api_key_scheme),
    bearer: Optional[HTTPAuthorizationCredentials] = Depends(bearer_scheme),
) -> AuthContext:
    """
    Optional authentication - returns public context if not authenticated.
    Never raises authentication errors.
    """
    request_id = getattr(request.state, "request_id", "unknown")
    client_ip = _get_client_ip(request)

    # Try API key
    if api_key:
        result = _authenticate_api_key(api_key, request_id, client_ip)
        if result.success:
            return result.context

    # Try JWT
    if bearer:
        result = await _authenticate_jwt(bearer.credentials, request_id, client_ip)
        if result.success:
            return result.context

    # Return public context
    return AuthContext(
        is_authenticated=False,
        roles=[Role.PUBLIC],
        permissions=get_permissions_for_roles([Role.PUBLIC]),
        request_id=request_id,
        client_ip=client_ip,
    )


# =============================================================================
# Token Management Endpoints Support
# =============================================================================

async def create_session_token(
    subject: str,
    roles: Optional[list[str]] = None,
) -> dict:
    """
    Create a new session with JWT tokens.

    Returns dict with access_token, refresh_token, and expires_in.
    """
    from app.core.jwt import get_jwt_manager, is_jwt_available

    if not is_jwt_available():
        raise HTTPException(
            status_code=501,
            detail="JWT authentication not configured"
        )

    jwt_manager = get_jwt_manager()

    # Convert role strings to Role enums for validation
    role_enums = []
    if roles:
        for role_str in roles:
            try:
                role_enums.append(Role(role_str))
            except ValueError:
                pass

    if not role_enums:
        role_enums = [Role.USER]

    token_pair = jwt_manager.create_token_pair(
        subject=subject,
        roles=[r.value for r in role_enums],
    )

    return {
        "access_token": token_pair.access_token,
        "refresh_token": token_pair.refresh_token,
        "token_type": token_pair.token_type,
        "expires_in": token_pair.expires_in,
    }


async def refresh_session_token(refresh_token: str) -> Optional[dict]:
    """
    Refresh an access token using a refresh token.

    Returns new access token or None if refresh token is invalid.
    """
    from app.core.jwt import get_jwt_manager, is_jwt_available

    if not is_jwt_available():
        return None

    jwt_manager = get_jwt_manager()
    new_access_token = jwt_manager.refresh_access_token(refresh_token)

    if not new_access_token:
        return None

    return {
        "access_token": new_access_token,
        "token_type": "bearer",
        "expires_in": jwt_manager.config.access_token_expire_minutes * 60,
    }


async def revoke_token(token: str) -> bool:
    """Revoke (blacklist) a token."""
    from app.core.jwt import get_jwt_manager, is_jwt_available

    if not is_jwt_available():
        return False

    jwt_manager = get_jwt_manager()
    return jwt_manager.blacklist_token(token)
