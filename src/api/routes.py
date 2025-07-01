import time
import structlog
from fastapi import APIRouter, HTTPException, Depends, Request
from fastapi.responses import JSONResponse

from api.models import EvaluationRequest, EvaluationResponse, ErrorResponse, HealthResponse
from core.evaluator import get_evaluation_engine
from core.exceptions import RateLimitExceeded, ServiceUnavailable, EvaluationError
from utils.metrics import REQUEST_COUNT, REQUEST_DURATION, ERROR_COUNT

router = APIRouter()
logger = structlog.get_logger()

@router.post("/evaluate", response_model=EvaluationResponse)
async def evaluate_llm_output(
    request: EvaluationRequest,
    evaluation_engine=Depends(get_evaluation_engine)
):
    """Evaluate LLM output against specified criteria"""
    start_time = time.time()
    
    try:
        REQUEST_COUNT.inc()
        
        result = await evaluation_engine.evaluate(
            input_text=request.input,
            output_text=request.output,
            criteria=request.criteria
        )
        
        evaluation_time_ms = int((time.time() - start_time) * 1000)
        REQUEST_DURATION.observe(time.time() - start_time)
        
        return EvaluationResponse(
            success=True,
            explanation=result.explanation,
            confidence=result.confidence,
            evaluation_time_ms=evaluation_time_ms,
            provider=result.provider,
            criteria_scores=result.criteria_scores
        )
        
    except RateLimitExceeded as e:
        ERROR_COUNT.labels(error_type="rate_limited").inc()
        logger.warning("Rate limit exceeded", error=str(e))
        return JSONResponse(
            status_code=429,
            content=ErrorResponse(
                explanation="Rate limit exceeded, please retry later",
                error_code="RATE_LIMITED",
                retry_after=60
            ).dict()
        )
        
    except ServiceUnavailable as e:
        ERROR_COUNT.labels(error_type="service_unavailable").inc()
        logger.error("Service unavailable", error=str(e))
        return JSONResponse(
            status_code=503,
            content=ErrorResponse(
                explanation="All LLM providers are currently unavailable",
                error_code="SERVICE_UNAVAILABLE"
            ).dict()
        )
        
    except EvaluationError as e:
        ERROR_COUNT.labels(error_type="evaluation_error").inc()
        logger.error("Evaluation error", error=str(e))
        return JSONResponse(
            status_code=400,
            content=ErrorResponse(
                explanation=f"Evaluation failed: {str(e)}",
                error_code="EVALUATION_ERROR"
            ).dict()
        )
        
    except Exception as e:
        ERROR_COUNT.labels(error_type="internal_error").inc()
        logger.error("Unexpected error during evaluation", exc_info=e)
        return JSONResponse(
            status_code=500,
            content=ErrorResponse(
                explanation="Internal server error occurred",
                error_code="INTERNAL_ERROR"
            ).dict()
        )

@router.get("/health", response_model=HealthResponse)
async def health_check():
    """Basic health check endpoint"""
    return HealthResponse(
        status="healthy",
        timestamp=str(int(time.time()))
    )

@router.get("/health/ready", response_model=HealthResponse)
async def readiness_check(evaluation_engine=Depends(get_evaluation_engine)):
    """Readiness probe - checks external dependencies"""
    try:
        components = await evaluation_engine.health_check()
        
        if all(status == "healthy" for status in components.values()):
            return HealthResponse(
                status="ready",
                timestamp=str(int(time.time())),
                components=components
            )
        else:
            return JSONResponse(
                status_code=503,
                content=HealthResponse(
                    status="not_ready",
                    timestamp=str(int(time.time())),
                    components=components
                ).dict()
            )
            
    except Exception as e:
        logger.error("Health check failed", exc_info=e)
        return JSONResponse(
            status_code=503,
            content=ErrorResponse(
                explanation="Health check failed",
                error_code="HEALTH_CHECK_FAILED"
            ).dict()
        )
