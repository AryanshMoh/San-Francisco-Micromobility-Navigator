"""Security utilities for API authentication and authorization."""

import hashlib
import hmac
import secrets
import time
from typing import Optional, Tuple

from fastapi import HTTPException, Request, Security
from fastapi.security import APIKeyHeader

from app.config import settings


# API Key header scheme
api_key_header = APIKeyHeader(
    name=settings.api_key_header,
    auto_error=False,
    description="API key for authentication"
)


class APIKeyValidator:
    """Validates API keys with timing-safe comparison."""

    def __init__(self):
        self._keys_hash_cache: dict[str, str] = {}
        self._refresh_keys()

    def _refresh_keys(self) -> None:
        """Refresh the cached key hashes."""
        self._keys_hash_cache = {
            self._hash_key(key): key
            for key in settings.get_api_keys_list()
        }

    def _hash_key(self, key: str) -> str:
        """Hash an API key for storage/comparison."""
        return hashlib.sha256(key.encode()).hexdigest()

    def validate(self, api_key: Optional[str]) -> Tuple[bool, Optional[str]]:
        """
        Validate an API key using timing-safe comparison.

        Returns:
            Tuple of (is_valid, error_message)
        """
        # Check if API key is required
        if not settings.api_key_required:
            # In development, allow requests without API key
            if not api_key:
                return True, None
            # But if provided, still validate it
            if not settings.get_api_keys_list():
                return True, None

        # API key is required but not provided
        if not api_key:
            return False, "API key is required"

        # Validate key format
        if len(api_key) < 32:
            return False, "Invalid API key format"

        # Check against valid keys using timing-safe comparison
        api_key_hash = self._hash_key(api_key)
        valid_keys = settings.get_api_keys_list()

        if not valid_keys:
            # No keys configured - deny in production, allow in dev
            if settings.is_production():
                return False, "No API keys configured"
            return True, None

        # Timing-safe comparison against all keys
        is_valid = False
        for valid_key in valid_keys:
            if hmac.compare_digest(api_key, valid_key):
                is_valid = True
                break

        if not is_valid:
            return False, "Invalid API key"

        return True, None


# Global validator instance
api_key_validator = APIKeyValidator()


async def verify_api_key(
    request: Request,
    api_key: Optional[str] = Security(api_key_header)
) -> Optional[str]:
    """
    FastAPI dependency for API key verification.

    Usage:
        @app.get("/protected")
        async def protected_endpoint(api_key: str = Depends(verify_api_key)):
            ...
    """
    is_valid, error_message = api_key_validator.validate(api_key)

    if not is_valid:
        raise HTTPException(
            status_code=401,
            detail=error_message or "Authentication required",
            headers={"WWW-Authenticate": "ApiKey"}
        )

    return api_key


async def optional_api_key(
    request: Request,
    api_key: Optional[str] = Security(api_key_header)
) -> Optional[str]:
    """
    FastAPI dependency for optional API key verification.
    Returns None if no key provided, validates if provided.
    """
    if not api_key:
        return None

    is_valid, error_message = api_key_validator.validate(api_key)

    if not is_valid:
        raise HTTPException(
            status_code=401,
            detail=error_message or "Invalid API key",
            headers={"WWW-Authenticate": "ApiKey"}
        )

    return api_key


def generate_api_key(prefix: str = "sk") -> str:
    """
    Generate a secure API key with optional prefix.

    Format: {prefix}_{random_token}
    Example: sk_a1b2c3d4e5f6g7h8i9j0...
    """
    token = secrets.token_urlsafe(32)
    return f"{prefix}_{token}"


def mask_api_key(api_key: str) -> str:
    """
    Mask an API key for logging purposes.

    Example: sk_a1b2c3d4... -> sk_a1b2****
    """
    if not api_key or len(api_key) < 12:
        return "****"

    # Show prefix and first 4 chars, mask the rest
    if "_" in api_key:
        prefix, token = api_key.split("_", 1)
        return f"{prefix}_{token[:4]}{'*' * 8}"

    return f"{api_key[:8]}{'*' * 8}"


class RateLimitExceeded(Exception):
    """Exception raised when rate limit is exceeded."""

    def __init__(self, retry_after: int):
        self.retry_after = retry_after
        super().__init__(f"Rate limit exceeded. Retry after {retry_after} seconds.")
