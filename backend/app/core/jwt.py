"""JWT token management for session authentication."""

import logging
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional
from uuid import uuid4

from pydantic import BaseModel, Field

from app.config import settings

logger = logging.getLogger("api.auth")

# JWT is optional - only import if needed
try:
    import jwt
    JWT_AVAILABLE = True
except ImportError:
    JWT_AVAILABLE = False
    logger.warning("PyJWT not installed. JWT authentication disabled.")


class TokenPayload(BaseModel):
    """JWT token payload structure."""

    sub: str = Field(..., description="Subject (user/session ID)")
    exp: datetime = Field(..., description="Expiration time")
    iat: datetime = Field(..., description="Issued at time")
    jti: str = Field(..., description="JWT ID (unique token identifier)")
    type: str = Field(default="access", description="Token type: access or refresh")
    roles: list[str] = Field(default_factory=list, description="User roles")
    permissions: list[str] = Field(default_factory=list, description="Specific permissions")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional claims")


class TokenPair(BaseModel):
    """Access and refresh token pair."""

    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int  # seconds until access token expires


class JWTConfig(BaseModel):
    """JWT configuration."""

    secret_key: str
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    refresh_token_expire_days: int = 7
    issuer: str = "sf-micromobility-api"
    audience: str = "sf-micromobility-client"


class JWTManager:
    """
    Manages JWT token creation, validation, and refresh.

    Features:
    - Access and refresh token generation
    - Token validation with expiry checking
    - Role and permission claims
    - Token blacklisting support (via Redis with in-memory fallback)
    - Secure token refresh flow
    """

    def __init__(self, config: Optional[JWTConfig] = None):
        if not JWT_AVAILABLE:
            raise RuntimeError("PyJWT is required for JWT authentication. Install with: pip install PyJWT")

        self.config = config or JWTConfig(
            secret_key=settings.secret_key,
            access_token_expire_minutes=getattr(settings, 'jwt_access_expire_minutes', 30),
            refresh_token_expire_days=getattr(settings, 'jwt_refresh_expire_days', 7),
        )

        # In-memory blacklist as fallback (not suitable for production multi-instance)
        self._blacklist: set[str] = set()

        # Redis client for persistent blacklist
        self._redis = None
        self._redis_available = False
        self._init_redis()

    def _init_redis(self) -> None:
        """Initialize Redis connection for token blacklist."""
        try:
            import redis
            redis_url = getattr(settings, 'redis_url', None)
            if redis_url:
                self._redis = redis.from_url(redis_url, decode_responses=True)
                # Test connection
                self._redis.ping()
                self._redis_available = True
                logger.info("JWT blacklist using Redis")
            else:
                logger.warning("Redis URL not configured, JWT blacklist using in-memory store (not suitable for production)")
        except ImportError:
            logger.warning("redis package not installed, JWT blacklist using in-memory store")
        except Exception as e:
            logger.warning(f"Failed to connect to Redis for JWT blacklist: {e}")

    def _is_token_blacklisted(self, jti: str) -> bool:
        """Check if a token JTI is blacklisted."""
        # Try Redis first
        if self._redis_available and self._redis:
            try:
                return self._redis.exists(f"jwt:blacklist:{jti}") > 0
            except Exception as e:
                logger.warning(f"Redis blacklist check failed: {e}")
                # Fall through to in-memory check

        # Fallback to in-memory
        return jti in self._blacklist

    def _add_to_blacklist(self, jti: str, exp: datetime) -> bool:
        """Add a token JTI to the blacklist with TTL."""
        # Calculate TTL (time until token expires)
        now = datetime.now(timezone.utc)
        ttl_seconds = max(int((exp - now).total_seconds()), 1)

        # Try Redis first
        if self._redis_available and self._redis:
            try:
                self._redis.setex(f"jwt:blacklist:{jti}", ttl_seconds, "1")
                logger.info(f"Token blacklisted in Redis: {jti[:8]}... (TTL: {ttl_seconds}s)")
                return True
            except Exception as e:
                logger.error(f"Failed to blacklist token in Redis: {e}")
                # Fall through to in-memory

        # Fallback to in-memory (warning: doesn't persist across restarts)
        self._blacklist.add(jti)
        logger.warning(f"Token blacklisted in-memory only: {jti[:8]}... (will not persist)")
        return True

    def create_access_token(
        self,
        subject: str,
        roles: Optional[list[str]] = None,
        permissions: Optional[list[str]] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> str:
        """
        Create a new access token.

        Args:
            subject: User or session identifier
            roles: List of role names
            permissions: List of specific permissions
            metadata: Additional claims to include

        Returns:
            Encoded JWT access token
        """
        now = datetime.now(timezone.utc)
        expire = now + timedelta(minutes=self.config.access_token_expire_minutes)

        payload = {
            "sub": subject,
            "exp": expire,
            "iat": now,
            "jti": str(uuid4()),
            "type": "access",
            "roles": roles or [],
            "permissions": permissions or [],
            "iss": self.config.issuer,
            "aud": self.config.audience,
        }

        if metadata:
            payload["metadata"] = metadata

        return jwt.encode(payload, self.config.secret_key, algorithm=self.config.algorithm)

    def create_refresh_token(self, subject: str) -> str:
        """
        Create a new refresh token.

        Refresh tokens have longer expiry and fewer claims.
        """
        now = datetime.now(timezone.utc)
        expire = now + timedelta(days=self.config.refresh_token_expire_days)

        payload = {
            "sub": subject,
            "exp": expire,
            "iat": now,
            "jti": str(uuid4()),
            "type": "refresh",
            "iss": self.config.issuer,
            "aud": self.config.audience,
        }

        return jwt.encode(payload, self.config.secret_key, algorithm=self.config.algorithm)

    def create_token_pair(
        self,
        subject: str,
        roles: Optional[list[str]] = None,
        permissions: Optional[list[str]] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> TokenPair:
        """Create both access and refresh tokens."""
        return TokenPair(
            access_token=self.create_access_token(subject, roles, permissions, metadata),
            refresh_token=self.create_refresh_token(subject),
            expires_in=self.config.access_token_expire_minutes * 60,
        )

    def decode_token(self, token: str) -> Optional[TokenPayload]:
        """
        Decode and validate a JWT token.

        Returns:
            TokenPayload if valid, None if invalid or expired
        """
        try:
            payload = jwt.decode(
                token,
                self.config.secret_key,
                algorithms=[self.config.algorithm],
                audience=self.config.audience,
                issuer=self.config.issuer,
            )

            # Check if token is blacklisted (Redis or in-memory)
            jti = payload.get("jti")
            if jti and self._is_token_blacklisted(jti):
                logger.warning(f"Attempted use of blacklisted token: {jti[:8]}...")
                return None

            return TokenPayload(
                sub=payload["sub"],
                exp=datetime.fromtimestamp(payload["exp"], tz=timezone.utc),
                iat=datetime.fromtimestamp(payload["iat"], tz=timezone.utc),
                jti=payload.get("jti", ""),
                type=payload.get("type", "access"),
                roles=payload.get("roles", []),
                permissions=payload.get("permissions", []),
                metadata=payload.get("metadata", {}),
            )

        except jwt.ExpiredSignatureError:
            logger.debug("Token expired")
            return None
        except jwt.InvalidTokenError as e:
            logger.warning(f"Invalid token: {e}")
            return None

    def refresh_access_token(
        self,
        refresh_token: str,
        roles: Optional[list[str]] = None,
        permissions: Optional[list[str]] = None,
    ) -> Optional[str]:
        """
        Create new access token using refresh token.

        Returns:
            New access token if refresh token is valid, None otherwise
        """
        payload = self.decode_token(refresh_token)

        if not payload:
            return None

        if payload.type != "refresh":
            logger.warning("Attempted to refresh with non-refresh token")
            return None

        return self.create_access_token(
            subject=payload.sub,
            roles=roles,
            permissions=permissions,
        )

    def blacklist_token(self, token: str) -> bool:
        """
        Add a token to the blacklist (logout).

        Uses Redis with TTL matching token expiry for persistent blacklisting.
        Falls back to in-memory if Redis is unavailable.
        """
        try:
            payload = jwt.decode(
                token,
                self.config.secret_key,
                algorithms=[self.config.algorithm],
                options={
                    "verify_exp": False,  # Allow blacklisting expired tokens
                    "verify_aud": False,  # Skip audience validation for JTI extraction
                    "verify_iss": False,  # Skip issuer validation for JTI extraction
                },
            )
            jti = payload.get("jti")
            exp_timestamp = payload.get("exp")

            if not jti:
                logger.warning("Token has no JTI, cannot blacklist")
                return False

            # Get expiry time for TTL
            if exp_timestamp:
                exp = datetime.fromtimestamp(exp_timestamp, tz=timezone.utc)
            else:
                # If no expiry, use max refresh token lifetime
                exp = datetime.now(timezone.utc) + timedelta(days=self.config.refresh_token_expire_days)

            return self._add_to_blacklist(jti, exp)

        except jwt.InvalidTokenError as e:
            logger.warning(f"Cannot blacklist invalid token: {e}")
            return False

    def verify_token_type(self, token: str, expected_type: str) -> bool:
        """Verify token is of expected type (access or refresh)."""
        payload = self.decode_token(token)
        return payload is not None and payload.type == expected_type


# Lazy initialization - only create if JWT is available
_jwt_manager: Optional[JWTManager] = None


def get_jwt_manager() -> JWTManager:
    """Get or create the JWT manager instance."""
    global _jwt_manager
    if _jwt_manager is None:
        if not JWT_AVAILABLE:
            raise RuntimeError("PyJWT not installed")
        _jwt_manager = JWTManager()
    return _jwt_manager


def is_jwt_available() -> bool:
    """Check if JWT authentication is available."""
    return JWT_AVAILABLE
