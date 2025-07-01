import asyncio
import structlog
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from prometheus_client import make_asgi_app, Counter, Histogram, Gauge
import time

from api.routes import router
from core.config import settings
from core.evaluator import EvaluationEngine
from core.rate_limiter import RedisRateLimiter
from core.circuit_breaker import CircuitBreaker
from providers.provider_pool import ProviderPool
from utils.metrics import setup_metrics
from utils.logging import setup_logging

# Global variables for dependency injection
evaluation_engine = None
logger = structlog.get_logger()

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan management"""
    global evaluation_engine
    
    # Startup
    setup_logging()
    setup_metrics()
    
    logger.info("Starting LLM Evaluation Service")
    
    # Initialize components
    provider_pool = ProviderPool()
    rate_limiter = RedisRateLimiter()
    circuit_breaker = CircuitBreaker()
    
    evaluation_engine = EvaluationEngine(
        provider_pool=provider_pool,
        rate_limiter=rate_limiter,
        circuit_breaker=circuit_breaker
    )
    
    await evaluation_engine.initialize()
    logger.info("Service initialized successfully")
    
    yield
    
    # Shutdown
    logger.info("Shutting down service")
    await evaluation_engine.cleanup()

app = FastAPI(
    title="LLM Evaluation Service",
    description="Scalable service for evaluating LLM outputs against criteria",
    version="1.0.0",
    lifespan=lifespan
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Add metrics endpoint
metrics_app = make_asgi_app()
app.mount("/metrics", metrics_app)

# Include API routes
app.include_router(router)

# Global exception handler
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error("Unhandled exception", exc_info=exc)
    return JSONResponse(
        status_code=500,
        content={
            "success": False,
            "explanation": "Internal server error occurred",
            "error_code": "INTERNAL_ERROR"
        }
    )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.DEBUG,
        access_log=False
    )
