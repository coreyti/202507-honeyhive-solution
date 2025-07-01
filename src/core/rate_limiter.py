import time
import asyncio
import structlog
import redis.asyncio as redis
from typing import Optional

from core.config import settings
from core.exceptions import RateLimitExceeded

logger = structlog.get_logger()

class RedisRateLimiter:
    def __init__(self):
        self.redis_client: Optional[redis.Redis] = None
        self.rate_limit = settings.RATE_LIMIT_PER_MINUTE
        self.window_size = 60  # 1 minute window

    async def initialize(self):
        """Initialize Redis connection"""
        try:
            self.redis_client = redis.from_url(
                settings.REDIS_URL,
                encoding="utf-8",
                decode_responses=True,
                socket_timeout=5,
                socket_connect_timeout=5
            )
            await self.redis_client.ping()
            logger.info("Redis rate limiter initialized")
        except Exception as e:
            logger.error("Failed to initialize Redis", error=str(e))
            raise

    async def cleanup(self):
        """Cleanup Redis connection"""
        if self.redis_client:
            await self.redis_client.close()

    async def acquire(self, key: str = "global") -> None:
        """Acquire rate limit token using sliding window"""
        if not self.redis_client:
            logger.warning("Redis not available, skipping rate limiting")
            return

        current_time = time.time()
        window_start = current_time - self.window_size
        rate_limit_key = f"rate_limit:{key}"

        try:
            # Use Redis pipeline for atomic operations
            pipe = self.redis_client.pipeline()
            
            # Remove expired entries
            pipe.zremrangebyscore(rate_limit_key, 0, window_start)
            
            # Count current requests in window
            pipe.zcard(rate_limit_key)
            
            # Add current request
            pipe.zadd(rate_limit_key, {str(current_time): current_time})
            
            # Set expiration
            pipe.expire(rate_limit_key, self.window_size)
            
            results = await pipe.execute()
            current_count = results[1]
            
            if current_count >= self.rate_limit:
                # Remove the request we just added since we're over limit
                await self.redis_client.zrem(rate_limit_key, str(current_time))
                raise RateLimitExceeded(f"Rate limit exceeded: {current_count}/{self.rate_limit} requests per minute")
                
            logger.debug("Rate limit check passed", count=current_count, limit=self.rate_limit)
            
        except redis.RedisError as e:
            logger.error("Redis rate limiting failed", error=str(e))
            # Continue without rate limiting on Redis failure
            pass

    async def health_check(self) -> bool:
        """Check Redis health"""
        if not self.redis_client:
            return False
        try:
            await self.redis_client.ping()
            return True
        except Exception:
            return False
