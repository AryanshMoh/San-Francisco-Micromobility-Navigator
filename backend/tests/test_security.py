"""Security tests for Phase 1 hardening."""

import pytest
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient

from app.config import Settings, generate_api_key
from app.core.security import (
    APIKeyValidator,
    mask_api_key,
    verify_api_key,
)


# =============================================================================
# Configuration Tests
# =============================================================================

class TestSecurityConfiguration:
    """Tests for security configuration validation."""

    def test_default_settings_not_production_safe(self):
        """Default settings should fail production validation."""
        settings = Settings(app_env="production")
        errors = settings.validate_production_settings()

        assert len(errors) > 0
        assert any("SECRET_KEY" in e for e in errors)

    def test_development_settings_allow_defaults(self):
        """Development mode should allow default values."""
        settings = Settings(app_env="development")
        errors = settings.validate_production_settings()

        # Should have no errors in development
        assert len(errors) == 0

    def test_production_requires_secure_secret_key(self):
        """Production should require a secure secret key."""
        settings = Settings(
            app_env="production",
            secret_key="dev-only-change-in-production"
        )
        errors = settings.validate_production_settings()

        assert any("SECRET_KEY must be changed" in e for e in errors)

    def test_production_requires_secure_database(self):
        """Production should reject default database password."""
        settings = Settings(
            app_env="production",
            secret_key="a" * 64,
            database_url="postgresql+asyncpg://user:devpassword@localhost/db"
        )
        errors = settings.validate_production_settings()

        assert any("devpassword" in e for e in errors)

    def test_api_key_parsing(self):
        """API keys should be parsed from comma-separated string."""
        key1 = generate_api_key()
        key2 = generate_api_key()
        settings = Settings(api_keys=f"{key1},{key2}")

        keys = settings.get_api_keys_list()
        assert len(keys) == 2
        assert key1 in keys
        assert key2 in keys

    def test_api_key_minimum_length(self):
        """API keys must meet minimum length requirement."""
        with pytest.raises(ValueError, match="at least 32 characters"):
            Settings(api_keys="short_key")


# =============================================================================
# API Key Validation Tests
# =============================================================================

class TestAPIKeyValidator:
    """Tests for API key validation."""

    def test_valid_api_key_accepted(self):
        """Valid API key should be accepted."""
        key = generate_api_key()

        with patch('app.core.security.settings') as mock_settings:
            mock_settings.api_key_required = True
            mock_settings.get_api_keys_list.return_value = [key]
            mock_settings.is_production.return_value = False

            validator = APIKeyValidator()
            is_valid, error = validator.validate(key)

            assert is_valid is True
            assert error is None

    def test_invalid_api_key_rejected(self):
        """Invalid API key should be rejected."""
        valid_key = generate_api_key()
        invalid_key = generate_api_key()

        with patch('app.core.security.settings') as mock_settings:
            mock_settings.api_key_required = True
            mock_settings.get_api_keys_list.return_value = [valid_key]
            mock_settings.is_production.return_value = False

            validator = APIKeyValidator()
            is_valid, error = validator.validate(invalid_key)

            assert is_valid is False
            assert "Invalid API key" in error

    def test_missing_key_rejected_when_required(self):
        """Missing API key should be rejected when required."""
        with patch('app.core.security.settings') as mock_settings:
            mock_settings.api_key_required = True
            mock_settings.get_api_keys_list.return_value = [generate_api_key()]

            validator = APIKeyValidator()
            is_valid, error = validator.validate(None)

            assert is_valid is False
            assert "required" in error.lower()

    def test_missing_key_allowed_in_dev(self):
        """Missing API key allowed in development when not required."""
        with patch('app.core.security.settings') as mock_settings:
            mock_settings.api_key_required = False
            mock_settings.get_api_keys_list.return_value = []

            validator = APIKeyValidator()
            is_valid, error = validator.validate(None)

            assert is_valid is True
            assert error is None

    def test_short_key_rejected(self):
        """Keys shorter than 32 chars should be rejected."""
        with patch('app.core.security.settings') as mock_settings:
            mock_settings.api_key_required = True
            mock_settings.get_api_keys_list.return_value = [generate_api_key()]

            validator = APIKeyValidator()
            is_valid, error = validator.validate("short")

            assert is_valid is False
            assert "format" in error.lower()


# =============================================================================
# API Key Utility Tests
# =============================================================================

class TestAPIKeyUtilities:
    """Tests for API key utility functions."""

    def test_generate_api_key_format(self):
        """Generated keys should have correct format."""
        key = generate_api_key()

        assert key.startswith("sk_")
        assert len(key) >= 32

    def test_generate_api_key_uniqueness(self):
        """Generated keys should be unique."""
        keys = [generate_api_key() for _ in range(100)]
        assert len(set(keys)) == 100

    def test_mask_api_key(self):
        """API key masking should hide most of the key."""
        key = "sk_a1b2c3d4e5f6g7h8i9j0k1l2m3n4o5p6"
        masked = mask_api_key(key)

        assert "sk_" in masked
        assert "a1b2" in masked
        assert "****" in masked
        assert key not in masked

    def test_mask_short_key(self):
        """Short keys should be fully masked."""
        masked = mask_api_key("short")
        assert masked == "****"

    def test_mask_empty_key(self):
        """Empty keys should be masked."""
        assert mask_api_key("") == "****"
        assert mask_api_key(None) == "****"


# =============================================================================
# Rate Limiting Tests
# =============================================================================

class TestRateLimiting:
    """Tests for rate limiting functionality."""

    @pytest.mark.asyncio
    async def test_in_memory_rate_limiter_allows_under_limit(self):
        """Requests under limit should be allowed."""
        from app.middleware.rate_limit import InMemoryRateLimiter

        limiter = InMemoryRateLimiter()
        key = "test_client"

        # Make requests under limit
        for i in range(5):
            is_allowed, remaining, retry_after = await limiter.is_allowed(key, 10, 60)
            assert is_allowed is True
            assert remaining == 10 - i - 1
            assert retry_after == 0

    @pytest.mark.asyncio
    async def test_in_memory_rate_limiter_blocks_over_limit(self):
        """Requests over limit should be blocked."""
        from app.middleware.rate_limit import InMemoryRateLimiter

        limiter = InMemoryRateLimiter()
        key = "test_client"

        # Exhaust the limit
        for _ in range(5):
            await limiter.is_allowed(key, 5, 60)

        # Next request should be blocked
        is_allowed, remaining, retry_after = await limiter.is_allowed(key, 5, 60)
        assert is_allowed is False
        assert remaining == 0
        assert retry_after > 0


# =============================================================================
# Security Headers Tests
# =============================================================================

class TestSecurityHeaders:
    """Tests for security headers middleware."""

    def test_security_headers_present(self):
        """Security headers should be present in responses."""
        # Import here to avoid circular imports
        from app.main import app
        client = TestClient(app)

        response = client.get("/health")

        assert response.headers.get("X-Content-Type-Options") == "nosniff"
        assert response.headers.get("X-Frame-Options") == "DENY"
        assert response.headers.get("X-XSS-Protection") == "1; mode=block"
        assert "Referrer-Policy" in response.headers

    def test_rate_limit_headers_present(self):
        """Rate limit headers should be present in responses."""
        from app.main import app
        client = TestClient(app)

        response = client.get("/health")

        assert "X-RateLimit-Limit" in response.headers
        assert "X-RateLimit-Remaining" in response.headers
        assert "X-RateLimit-Reset" in response.headers


# =============================================================================
# Integration Tests
# =============================================================================

class TestSecurityIntegration:
    """Integration tests for security features."""

    def test_health_endpoint_no_auth_required(self):
        """Health endpoint should not require authentication."""
        from app.main import app
        client = TestClient(app)

        response = client.get("/health")
        assert response.status_code == 200

    def test_admin_endpoint_requires_auth(self):
        """Admin endpoints should require authentication."""
        from app.main import app
        client = TestClient(app)

        # Without API key
        response = client.get("/admin/config")
        assert response.status_code == 401

    def test_request_id_in_response(self):
        """Request ID should be present in responses."""
        from app.main import app
        client = TestClient(app)

        response = client.get("/")
        assert "X-Request-ID" in response.headers


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
