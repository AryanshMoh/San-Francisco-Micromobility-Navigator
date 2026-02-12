"""Role-Based Access Control (RBAC) for API authorization."""

import logging
from enum import Enum
from functools import wraps
from typing import Callable, List, Optional, Set, Union

from fastapi import Depends, HTTPException, Request, status
from pydantic import BaseModel

from app.core.security import api_key_header
from app.core.exceptions import AuthorizationException, AuthenticationException
from app.config import settings

logger = logging.getLogger("api.rbac")


# =============================================================================
# Role and Permission Definitions
# =============================================================================

class Role(str, Enum):
    """System roles with hierarchical permissions."""

    # Public - no authentication required
    PUBLIC = "public"

    # Authenticated user - basic access
    USER = "user"

    # Verified user - can submit reports
    VERIFIED = "verified"

    # Moderator - can manage reports
    MODERATOR = "moderator"

    # Admin - full access
    ADMIN = "admin"

    # System - internal services
    SYSTEM = "system"


class Permission(str, Enum):
    """Granular permissions for fine-grained access control."""

    # Route permissions
    ROUTE_CALCULATE = "route:calculate"
    ROUTE_VIEW = "route:view"

    # Risk zone permissions
    RISK_ZONE_VIEW = "risk_zone:view"
    RISK_ZONE_CREATE = "risk_zone:create"
    RISK_ZONE_UPDATE = "risk_zone:update"
    RISK_ZONE_DELETE = "risk_zone:delete"

    # Report permissions
    REPORT_SUBMIT = "report:submit"
    REPORT_VIEW = "report:view"
    REPORT_VERIFY = "report:verify"
    REPORT_MODERATE = "report:moderate"
    REPORT_DELETE = "report:delete"

    # User permissions
    USER_VIEW = "user:view"
    USER_CREATE = "user:create"
    USER_UPDATE = "user:update"
    USER_DELETE = "user:delete"

    # Admin permissions
    ADMIN_VIEW_CONFIG = "admin:view_config"
    ADMIN_MANAGE_KEYS = "admin:manage_keys"
    ADMIN_VIEW_AUDIT = "admin:view_audit"
    ADMIN_MANAGE_USERS = "admin:manage_users"

    # System permissions
    SYSTEM_HEALTH = "system:health"
    SYSTEM_METRICS = "system:metrics"


# Role to permissions mapping
ROLE_PERMISSIONS: dict[Role, Set[Permission]] = {
    Role.PUBLIC: {
        Permission.ROUTE_CALCULATE,
        Permission.ROUTE_VIEW,
        Permission.RISK_ZONE_VIEW,
        Permission.SYSTEM_HEALTH,
    },

    Role.USER: {
        Permission.ROUTE_CALCULATE,
        Permission.ROUTE_VIEW,
        Permission.RISK_ZONE_VIEW,
        Permission.REPORT_VIEW,
        Permission.SYSTEM_HEALTH,
    },

    Role.VERIFIED: {
        Permission.ROUTE_CALCULATE,
        Permission.ROUTE_VIEW,
        Permission.RISK_ZONE_VIEW,
        Permission.REPORT_SUBMIT,
        Permission.REPORT_VIEW,
        Permission.REPORT_VERIFY,
        Permission.SYSTEM_HEALTH,
    },

    Role.MODERATOR: {
        Permission.ROUTE_CALCULATE,
        Permission.ROUTE_VIEW,
        Permission.RISK_ZONE_VIEW,
        Permission.RISK_ZONE_CREATE,
        Permission.RISK_ZONE_UPDATE,
        Permission.REPORT_SUBMIT,
        Permission.REPORT_VIEW,
        Permission.REPORT_VERIFY,
        Permission.REPORT_MODERATE,
        Permission.USER_VIEW,
        Permission.SYSTEM_HEALTH,
    },

    Role.ADMIN: set(Permission),  # All permissions

    Role.SYSTEM: set(Permission),  # All permissions
}


# =============================================================================
# Authorization Context
# =============================================================================

class AuthContext(BaseModel):
    """Authentication and authorization context for a request."""

    # Authentication
    is_authenticated: bool = False
    auth_method: Optional[str] = None  # "api_key", "jwt", "session"

    # Identity
    subject_id: Optional[str] = None  # User ID or API key identifier
    subject_type: str = "anonymous"  # "user", "service", "anonymous"

    # Authorization
    roles: List[Role] = []
    permissions: Set[Permission] = set()

    # Request context
    request_id: Optional[str] = None
    client_ip: Optional[str] = None

    class Config:
        arbitrary_types_allowed = True

    def has_role(self, role: Role) -> bool:
        """Check if context has a specific role."""
        return role in self.roles

    def has_any_role(self, roles: List[Role]) -> bool:
        """Check if context has any of the specified roles."""
        return any(role in self.roles for role in roles)

    def has_permission(self, permission: Permission) -> bool:
        """Check if context has a specific permission."""
        return permission in self.permissions

    def has_all_permissions(self, permissions: List[Permission]) -> bool:
        """Check if context has all specified permissions."""
        return all(p in self.permissions for p in permissions)

    def has_any_permission(self, permissions: List[Permission]) -> bool:
        """Check if context has any of the specified permissions."""
        return any(p in self.permissions for p in permissions)


# =============================================================================
# Authorization Functions
# =============================================================================

def get_permissions_for_roles(roles: List[Role]) -> Set[Permission]:
    """Get all permissions for a list of roles."""
    permissions = set()
    for role in roles:
        permissions.update(ROLE_PERMISSIONS.get(role, set()))
    return permissions


def get_auth_context_from_api_key(api_key: Optional[str]) -> AuthContext:
    """
    Create auth context from API key.

    In a full implementation, this would look up the API key in a database
    to get associated roles and permissions.
    """
    if not api_key:
        # Anonymous/public access
        return AuthContext(
            is_authenticated=False,
            roles=[Role.PUBLIC],
            permissions=get_permissions_for_roles([Role.PUBLIC]),
        )

    # Validate API key
    from app.core.security import api_key_validator
    is_valid, error = api_key_validator.validate(api_key)

    if not is_valid:
        return AuthContext(
            is_authenticated=False,
            roles=[Role.PUBLIC],
            permissions=get_permissions_for_roles([Role.PUBLIC]),
        )

    # API key is valid - grant admin role (in production, look up key's roles)
    # For now, all valid API keys get admin access
    return AuthContext(
        is_authenticated=True,
        auth_method="api_key",
        subject_id=api_key[:16] + "...",  # Masked key
        subject_type="service",
        roles=[Role.ADMIN],
        permissions=get_permissions_for_roles([Role.ADMIN]),
    )


async def get_auth_context(request: Request) -> AuthContext:
    """
    FastAPI dependency to get authentication context.

    Checks for:
    1. JWT Bearer token
    2. API key header
    3. Falls back to public access
    """
    request_id = getattr(request.state, "request_id", None)
    client_ip = _get_client_ip(request)

    # Check for API key first
    api_key = request.headers.get(settings.api_key_header)
    if api_key:
        context = get_auth_context_from_api_key(api_key)
        context.request_id = request_id
        context.client_ip = client_ip
        return context

    # Check for JWT Bearer token
    auth_header = request.headers.get("Authorization")
    if auth_header and auth_header.startswith("Bearer "):
        token = auth_header[7:]
        context = await _get_context_from_jwt(token)
        if context:
            context.request_id = request_id
            context.client_ip = client_ip
            return context

    # Public access
    return AuthContext(
        is_authenticated=False,
        roles=[Role.PUBLIC],
        permissions=get_permissions_for_roles([Role.PUBLIC]),
        request_id=request_id,
        client_ip=client_ip,
    )


async def _get_context_from_jwt(token: str) -> Optional[AuthContext]:
    """Extract auth context from JWT token."""
    try:
        from app.core.jwt import get_jwt_manager, is_jwt_available

        if not is_jwt_available():
            return None

        jwt_manager = get_jwt_manager()
        payload = jwt_manager.decode_token(token)

        if not payload:
            return None

        # Convert role strings to Role enums
        roles = []
        for role_str in payload.roles:
            try:
                roles.append(Role(role_str))
            except ValueError:
                logger.warning(f"Unknown role in token: {role_str}")

        if not roles:
            roles = [Role.USER]

        return AuthContext(
            is_authenticated=True,
            auth_method="jwt",
            subject_id=payload.sub,
            subject_type="user",
            roles=roles,
            permissions=get_permissions_for_roles(roles),
        )

    except Exception as e:
        logger.warning(f"JWT context extraction failed: {e}")
        return None


def _get_client_ip(request: Request) -> str:
    """Extract client IP from request."""
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()
    if request.client:
        return request.client.host
    return "unknown"


# =============================================================================
# Authorization Dependencies
# =============================================================================

def require_auth(
    context: AuthContext = Depends(get_auth_context)
) -> AuthContext:
    """Require any form of authentication."""
    if not context.is_authenticated:
        raise AuthenticationException("Authentication required")
    return context


def require_roles(*roles: Role):
    """
    Require one or more specific roles.

    Usage:
        @app.get("/admin")
        async def admin_endpoint(context: AuthContext = Depends(require_roles(Role.ADMIN))):
            ...
    """
    async def dependency(context: AuthContext = Depends(get_auth_context)) -> AuthContext:
        if not context.is_authenticated:
            raise AuthenticationException("Authentication required")

        if not context.has_any_role(list(roles)):
            logger.warning(
                f"Access denied for {context.subject_id}: "
                f"required roles {[r.value for r in roles]}, "
                f"has roles {[r.value for r in context.roles]}"
            )
            raise AuthorizationException(
                f"Insufficient permissions. Required role: {' or '.join(r.value for r in roles)}"
            )

        return context

    return dependency


def require_permissions(*permissions: Permission):
    """
    Require one or more specific permissions.

    Usage:
        @app.post("/reports")
        async def submit_report(context: AuthContext = Depends(require_permissions(Permission.REPORT_SUBMIT))):
            ...
    """
    async def dependency(context: AuthContext = Depends(get_auth_context)) -> AuthContext:
        if not context.is_authenticated:
            raise AuthenticationException("Authentication required")

        missing = [p for p in permissions if p not in context.permissions]
        if missing:
            logger.warning(
                f"Access denied for {context.subject_id}: "
                f"missing permissions {[p.value for p in missing]}"
            )
            raise AuthorizationException("Insufficient permissions")

        return context

    return dependency


def require_any_permission(*permissions: Permission):
    """Require at least one of the specified permissions."""
    async def dependency(context: AuthContext = Depends(get_auth_context)) -> AuthContext:
        if not context.is_authenticated:
            raise AuthenticationException("Authentication required")

        if not context.has_any_permission(list(permissions)):
            raise AuthorizationException("Insufficient permissions")

        return context

    return dependency


# =============================================================================
# Permission Checking Utilities
# =============================================================================

def check_permission(context: AuthContext, permission: Permission) -> bool:
    """Check if context has permission without raising exception."""
    return context.has_permission(permission)


def check_role(context: AuthContext, role: Role) -> bool:
    """Check if context has role without raising exception."""
    return context.has_role(role)


def check_resource_access(
    context: AuthContext,
    resource_owner_id: Optional[str],
    admin_override: bool = True
) -> bool:
    """
    Check if context can access a resource.

    Returns True if:
    - Context is admin (if admin_override is True)
    - Context subject matches resource owner
    """
    if admin_override and context.has_role(Role.ADMIN):
        return True

    if context.subject_id and context.subject_id == resource_owner_id:
        return True

    return False
