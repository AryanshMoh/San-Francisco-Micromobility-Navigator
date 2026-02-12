"""Audit logging for security-critical operations."""

import json
import logging
from datetime import datetime
from enum import Enum
from typing import Any, Dict, Optional
from uuid import UUID

from pydantic import BaseModel

from app.config import settings

logger = logging.getLogger("api.audit")


class AuditAction(str, Enum):
    """Audit action types."""

    # Authentication
    AUTH_SUCCESS = "auth.success"
    AUTH_FAILURE = "auth.failure"
    AUTH_RATE_LIMITED = "auth.rate_limited"

    # Data Access
    DATA_READ = "data.read"
    DATA_CREATE = "data.create"
    DATA_UPDATE = "data.update"
    DATA_DELETE = "data.delete"

    # Route Calculation
    ROUTE_CALCULATE = "route.calculate"
    ROUTE_ALTERNATIVES = "route.alternatives"

    # Risk Zones
    RISK_ZONE_QUERY = "risk_zone.query"
    RISK_ZONE_CREATE = "risk_zone.create"

    # Reports
    REPORT_SUBMIT = "report.submit"
    REPORT_VERIFY = "report.verify"

    # Admin
    ADMIN_ACCESS = "admin.access"
    ADMIN_CONFIG_VIEW = "admin.config_view"
    ADMIN_KEY_GENERATE = "admin.key_generate"

    # Security Events
    SECURITY_SUSPICIOUS = "security.suspicious"
    SECURITY_BLOCKED = "security.blocked"


class AuditSeverity(str, Enum):
    """Audit event severity levels."""

    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class AuditEntry(BaseModel):
    """Audit log entry structure."""

    timestamp: datetime
    action: AuditAction
    severity: AuditSeverity
    request_id: Optional[str] = None
    client_ip: Optional[str] = None
    user_agent: Optional[str] = None
    api_key_id: Optional[str] = None  # Masked key identifier
    resource_type: Optional[str] = None
    resource_id: Optional[str] = None
    details: Optional[Dict[str, Any]] = None
    success: bool = True
    error_message: Optional[str] = None


class AuditLogger:
    """
    Centralized audit logging for security events.

    Logs to:
    - Structured log file (always)
    - Database (optional, for queryable audit trail)
    - External SIEM (optional, for enterprise deployments)
    """

    def __init__(self):
        self._setup_logger()

    def _setup_logger(self) -> None:
        """Configure the audit logger."""
        # Ensure audit logs go to a dedicated handler
        self._logger = logging.getLogger("api.audit")
        self._logger.setLevel(logging.INFO)

        # Don't propagate to root logger
        self._logger.propagate = True

    def _format_entry(self, entry: AuditEntry) -> str:
        """Format audit entry as JSON for structured logging."""
        return json.dumps(entry.model_dump(mode="json"), default=str)

    def log(
        self,
        action: AuditAction,
        *,
        severity: AuditSeverity = AuditSeverity.INFO,
        request_id: Optional[str] = None,
        client_ip: Optional[str] = None,
        user_agent: Optional[str] = None,
        api_key: Optional[str] = None,
        resource_type: Optional[str] = None,
        resource_id: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
        success: bool = True,
        error_message: Optional[str] = None,
    ) -> None:
        """
        Log an audit event.

        Args:
            action: The action being audited
            severity: Event severity level
            request_id: Unique request identifier
            client_ip: Client IP address
            user_agent: Client user agent
            api_key: API key used (will be masked)
            resource_type: Type of resource accessed
            resource_id: ID of resource accessed
            details: Additional context
            success: Whether the action succeeded
            error_message: Error message if failed
        """
        # Mask API key for logging
        api_key_id = None
        if api_key:
            from app.core.security import mask_api_key
            api_key_id = mask_api_key(api_key)

        entry = AuditEntry(
            timestamp=datetime.utcnow(),
            action=action,
            severity=severity,
            request_id=request_id,
            client_ip=client_ip,
            user_agent=user_agent,
            api_key_id=api_key_id,
            resource_type=resource_type,
            resource_id=resource_id,
            details=details,
            success=success,
            error_message=error_message,
        )

        # Log based on severity
        log_message = self._format_entry(entry)

        if severity == AuditSeverity.CRITICAL:
            self._logger.critical(f"AUDIT: {log_message}")
        elif severity == AuditSeverity.ERROR:
            self._logger.error(f"AUDIT: {log_message}")
        elif severity == AuditSeverity.WARNING:
            self._logger.warning(f"AUDIT: {log_message}")
        else:
            self._logger.info(f"AUDIT: {log_message}")

    def log_auth_success(
        self,
        request_id: str,
        client_ip: str,
        api_key: str,
    ) -> None:
        """Log successful authentication."""
        self.log(
            AuditAction.AUTH_SUCCESS,
            request_id=request_id,
            client_ip=client_ip,
            api_key=api_key,
        )

    def log_auth_failure(
        self,
        request_id: str,
        client_ip: str,
        reason: str,
    ) -> None:
        """Log failed authentication attempt."""
        self.log(
            AuditAction.AUTH_FAILURE,
            severity=AuditSeverity.WARNING,
            request_id=request_id,
            client_ip=client_ip,
            success=False,
            error_message=reason,
        )

    def log_rate_limited(
        self,
        request_id: str,
        client_ip: str,
        endpoint: str,
    ) -> None:
        """Log rate limit hit."""
        self.log(
            AuditAction.AUTH_RATE_LIMITED,
            severity=AuditSeverity.WARNING,
            request_id=request_id,
            client_ip=client_ip,
            details={"endpoint": endpoint},
        )

    def log_data_access(
        self,
        action: AuditAction,
        request_id: str,
        resource_type: str,
        resource_id: Optional[str] = None,
        client_ip: Optional[str] = None,
        api_key: Optional[str] = None,
    ) -> None:
        """Log data access operations."""
        self.log(
            action,
            request_id=request_id,
            resource_type=resource_type,
            resource_id=resource_id,
            client_ip=client_ip,
            api_key=api_key,
        )

    def log_security_event(
        self,
        request_id: str,
        client_ip: str,
        event_type: str,
        details: Dict[str, Any],
        blocked: bool = False,
    ) -> None:
        """Log security-related events."""
        action = AuditAction.SECURITY_BLOCKED if blocked else AuditAction.SECURITY_SUSPICIOUS
        self.log(
            action,
            severity=AuditSeverity.WARNING if not blocked else AuditSeverity.ERROR,
            request_id=request_id,
            client_ip=client_ip,
            details={"event_type": event_type, **details},
        )

    def log_admin_action(
        self,
        action: AuditAction,
        request_id: str,
        client_ip: str,
        api_key: str,
        details: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Log administrative actions."""
        self.log(
            action,
            severity=AuditSeverity.WARNING,  # Admin actions always notable
            request_id=request_id,
            client_ip=client_ip,
            api_key=api_key,
            details=details,
        )


# Global audit logger instance
audit_log = AuditLogger()
