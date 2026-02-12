"""Core security, authentication, and authorization modules."""

# Security utilities
from app.core.security import (
    verify_api_key,
    optional_api_key,
    generate_api_key,
    mask_api_key,
    APIKeyValidator,
    RateLimitExceeded,
)

# Exception handling
from app.core.exceptions import (
    APIException,
    ValidationException,
    AuthenticationException,
    AuthorizationException,
    ResourceNotFoundException,
    RateLimitException,
    ServiceUnavailableException,
    RoutingException,
    register_exception_handlers,
    sanitize_error_message,
)

# Audit logging
from app.core.audit import (
    AuditAction,
    AuditSeverity,
    AuditLogger,
    audit_log,
)

# Role-Based Access Control
from app.core.rbac import (
    Role,
    Permission,
    AuthContext,
    get_auth_context,
    require_auth,
    require_roles,
    require_permissions,
    require_any_permission,
    check_permission,
    check_role,
    check_resource_access,
    get_permissions_for_roles,
)

# Unified authentication
from app.core.auth import (
    authenticate_request,
    require_authentication,
    optional_authentication,
    create_session_token,
    refresh_session_token,
    revoke_token,
)

__all__ = [
    # Security
    "verify_api_key",
    "optional_api_key",
    "generate_api_key",
    "mask_api_key",
    "APIKeyValidator",
    "RateLimitExceeded",
    # Exceptions
    "APIException",
    "ValidationException",
    "AuthenticationException",
    "AuthorizationException",
    "ResourceNotFoundException",
    "RateLimitException",
    "ServiceUnavailableException",
    "RoutingException",
    "register_exception_handlers",
    "sanitize_error_message",
    # Audit
    "AuditAction",
    "AuditSeverity",
    "AuditLogger",
    "audit_log",
    # RBAC
    "Role",
    "Permission",
    "AuthContext",
    "get_auth_context",
    "require_auth",
    "require_roles",
    "require_permissions",
    "require_any_permission",
    "check_permission",
    "check_role",
    "check_resource_access",
    "get_permissions_for_roles",
    # Authentication
    "authenticate_request",
    "require_authentication",
    "optional_authentication",
    "create_session_token",
    "refresh_session_token",
    "revoke_token",
]
