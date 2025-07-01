import time
import asyncio
import structlog
from typing import Callable, Any
from enum import Enum

from core.config import settings
from core.exceptions import CircuitBreakerOpen, ServiceUnavailable

logger = structlog.get_logger()

class CircuitBreakerState(Enum):
    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"

class CircuitBreaker:
    def __init__(self):
        self.failure_threshold = settings.CIRCUIT_BREAKER_THRESHOLD
        self.recovery_timeout = settings.CIRCUIT_BREAKER_TIMEOUT
        self.failure_count = 0
        self.last_failure_time = None
        self.state = CircuitBreakerState.CLOSED
        self.lock = asyncio.Lock()

    async def call(self, func: Callable, *args, **kwargs) -> Any:
        """Execute function through circuit breaker"""
        async with self.lock:
            if self.state == CircuitBreakerState.OPEN:
                if time.time() - self.last_failure_time < self.recovery_timeout:
                    logger.warning("Circuit breaker is open")
                    raise ServiceUnavailable("Circuit breaker is open")
                else:
                    # Transition to half-open
                    self.state = CircuitBreakerState.HALF_OPEN
                    logger.info("Circuit breaker transitioning to half-open")

        try:
            result = await func(*args, **kwargs)
            
            # Success - reset circuit breaker
            async with self.lock:
                if self.state == CircuitBreakerState.HALF_OPEN:
                    self.state = CircuitBreakerState.CLOSED
                    self.failure_count = 0
                    logger.info("Circuit breaker closed after successful call")
                
            return result
            
        except Exception as e:
            async with self.lock:
                self.failure_count += 1
                self.last_failure_time = time.time()
                
                if self.failure_count >= self.failure_threshold:
                    self.state = CircuitBreakerState.OPEN
                    logger.warning(
                        "Circuit breaker opened",
                        failure_count=self.failure_count,
                        threshold=self.failure_threshold
                    )
                
            raise
