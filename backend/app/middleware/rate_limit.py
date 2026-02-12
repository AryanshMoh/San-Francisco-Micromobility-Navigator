"""Rate limiting middleware using Redis for distributed rate limiting."""

import asyncio
import hashlib
import time
from typing import Callable, Optional, Tuple

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse

from app.config import settings


class InMemoryRateLimiter:
    """
    In-memory rate limiter for development/fallback.
    Uses sliding window algorithm.

    Note: This is NOT suitable for production with multiple instances.
    Use Redis-based rate limiting in production.
    """

    def __init__(self):
        self._requests: dict[str, list[float]] = {}
        self._lock = asyncio.Lock()

    async def is_allowed(
        self,
        key: str,
        max_requests: int,
        window_seconds: int
    ) -> Tuple[bool, int, int]:
        """
        Check if request is allowed under rate limit.

        Returns:
            Tuple of (is_allowed, remaining_requests, retry_after_seconds)
        """
        now = time.time()
        window_start = now - window_seconds

        async with self._lock:
            # Get existing requests for this key
            if key not in self._requests:
                self._requests[key] = []

            # Remove expired requests
            self._requests[key] = [
                ts for ts in self._requests[key]
                if ts > window_start
            ]

            current_count = len(self._requests[key])

            if current_count >= max_requests:
                # Calculate retry after (time until oldest request expires)
                oldest = min(self._requests[key]) if self._requests[key] else now
                retry_after = int(oldest + window_seconds - now) + 1
                return False, 0, max(1, retry_after)

            # Add current request
            self._requests[key].append(now)
            remaining = max_requests - current_count - 1

            return True, remaining, 0

    async def cleanup(self) -> None:
        """Remove expired entries to prevent memory growth."""
        now = time.time()
        window = settings.rate_limit_window_seconds

        async with self._lock:
            keys_to_remove = []
            for key, timestamps in self._requests.items():
                # Remove old timestamps
                self._requests[key] = [
                    ts for ts in timestamps
                    if ts > now - window
                ]
                # Mark empty keys for removal
                if not self._requests[key]:
                    keys_to_remove.append(key)

            for key in keys_to_remove:
                del self._requests[key]


class RedisRateLimiter:
    """
    Redis-based rate limiter for production use.
    Uses sliding window with Redis sorted sets.
    """

    def __init__(self, redis_url: str):
        self._redis_url = redis_url
        self._redis = None

    async def _get_redis(self):
        """Get or create Redis connection."""
        if self._redis is None:
            try:
                import redis.asyncio as redis
                self._redis = redis.from_url(
                    self._redis_url,
                    encoding="utf-8",
                    decode_responses=True
                )
            except Exception:
                return None
        return self._redis

    async def is_allowed(
        self,
        key: str,
        max_requests: int,
        window_seconds: int
    ) -> Tuple[bool, int, int]:
        """
        Check if request is allowed using Redis sliding window.

        Returns:
            Tuple of (is_allowed, remaining_requests, retry_after_seconds)
        """
        redis = await self._get_redis()
        if redis is None:
            # Fallback: allow request if Redis unavailable
            return True, max_requests, 0

        now = time.time()
        window_start = now - window_seconds
        rate_key = f"rate_limit:{key}"

        try:
            pipe = redis.pipeline()

            # Remove old entries
            pipe.zremrangebyscore(rate_key, 0, window_start)

            # Count current entries
            pipe.zcard(rate_key)

            # Add current request
            pipe.zadd(rate_key, {str(now): now})

            # Set expiry on the key
            pipe.expire(rate_key, window_seconds + 1)

            results = await pipe.execute()
            current_count = results[1]

            if current_count >= max_requests:
                # Get oldest timestamp to calculate retry_after
                oldest = await redis.zrange(rate_key, 0, 0, withscores=True)
                if oldest:
                    retry_after = int(oldest[0][1] + window_seconds - now) + 1
                else:
                    retry_after = window_seconds
                return False, 0, max(1, retry_after)

            remaining = max_requests - current_count - 1
            return True, remaining, 0

        except Exception:
            # Fallback: allow request if Redis fails
            return True, max_requests, 0

    async def close(self) -> None:
        """Close Redis connection."""
        if self._redis:
            await self._redis.close()


class RateLimitMiddleware(BaseHTTPMiddleware):
    """
    Rate limiting middleware for FastAPI.

    Features:
    - IP-based rate limiting
    - API key-based rate limiting (higher limits for authenticated requests)
    - Configurable limits via settings
    - Redis support for distributed deployments
    - Graceful fallback to in-memory when Redis unavailable
    """

    # Paths exempt from rate limiting
    EXEMPT_PATHS = {"/health", "/health/ready", "/health/db", "/docs", "/redoc", "/openapi.json"}

    def __init__(self, app, use_redis: bool = True):
        super().__init__(app)
        self._use_redis = use_redis
        self._memory_limiter = InMemoryRateLimiter()
        self._redis_limiter: Optional[RedisRateLimiter] = None

        if use_redis and settings.redis_url:
            self._redis_limiter = RedisRateLimiter(settings.redis_url)

    def _get_client_identifier(self, request: Request) -> str:
        """
        Get a unique identifier for the client.
        Uses API key if present, otherwise falls back to IP.
        """
        # Check for API key first
        api_key = request.headers.get(settings.api_key_header)
        if api_key:
            # Hash the API key for privacy
            return f"key:{hashlib.sha256(api_key.encode()).hexdigest()[:16]}"

        # Fall back to IP address
        forwarded = request.headers.get("X-Forwarded-For")
        if forwarded:
            # Get the first IP in the chain (client IP)
            client_ip = forwarded.split(",")[0].strip()
        else:
            client_ip = request.client.host if request.client else "unknown"

        return f"ip:{client_ip}"

    def _get_rate_limits(self, request: Request) -> Tuple[int, int]:
        """
        Get rate limits based on authentication status.

        Returns:
            Tuple of (max_requests, window_seconds)
        """
        api_key = request.headers.get(settings.api_key_header)

        if api_key:
            # Authenticated requests get higher limits
            return (
                settings.rate_limit_requests * 3,  # 3x limit for API key users
                settings.rate_limit_window_seconds
            )

        # Default limits for unauthenticated requests
        return (
            settings.rate_limit_requests,
            settings.rate_limit_window_seconds
        )

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Process the request with rate limiting."""

        # Skip rate limiting if disabled
        if not settings.rate_limit_enabled:
            return await call_next(request)

        # Skip exempt paths
        if request.url.path in self.EXEMPT_PATHS:
            return await call_next(request)

        # Get client identifier and rate limits
        client_id = self._get_client_identifier(request)
        max_requests, window_seconds = self._get_rate_limits(request)

        # Check rate limit
        limiter = self._redis_limiter if self._redis_limiter else self._memory_limiter
        is_allowed, remaining, retry_after = await limiter.is_allowed(
            client_id, max_requests, window_seconds
        )

        if not is_allowed:
            return JSONResponse(
                status_code=429,
                content={
                    "detail": "Rate limit exceeded",
                    "retry_after": retry_after
                },
                headers={
                    "Retry-After": str(retry_after),
                    "X-RateLimit-Limit": str(max_requests),
                    "X-RateLimit-Remaining": "0",
                    "X-RateLimit-Reset": str(int(time.time()) + retry_after)
                }
            )

        # Process request
        response = await call_next(request)

        # Add rate limit headers to response
        response.headers["X-RateLimit-Limit"] = str(max_requests)
        response.headers["X-RateLimit-Remaining"] = str(remaining)
        response.headers["X-RateLimit-Reset"] = str(
            int(time.time()) + window_seconds
        )

        return response
