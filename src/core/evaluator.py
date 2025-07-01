import asyncio
import structlog
from typing import Dict, Any, Optional
from dataclasses import dataclass

from core.config import settings
from core.rate_limiter import RedisRateLimiter
from core.circuit_breaker import CircuitBreaker
from core.exceptions import EvaluationError, ServiceUnavailable
from providers.provider_pool import ProviderPool
from utils.metrics import EVALUATION_COUNT, EVALUATION_DURATION

logger = structlog.get_logger()

@dataclass
class EvaluationResult:
    explanation: str
    confidence: Optional[float] = None
    provider: Optional[str] = None
    criteria_scores: Optional[Dict[str, float]] = None

class EvaluationEngine:
    def __init__(self, provider_pool: ProviderPool, rate_limiter: RedisRateLimiter, circuit_breaker: CircuitBreaker):
        self.provider_pool = provider_pool
        self.rate_limiter = rate_limiter
        self.circuit_breaker = circuit_breaker
        self.logger = logger

    async def initialize(self):
        """Initialize the evaluation engine"""
        await self.rate_limiter.initialize()
        await self.provider_pool.initialize()
        self.logger.info("Evaluation engine initialized")

    async def cleanup(self):
        """Cleanup resources"""
        await self.rate_limiter.cleanup()
        await self.provider_pool.cleanup()

    async def evaluate(self, input_text: str, output_text: str, criteria: str) -> EvaluationResult:
        """Evaluate LLM output against criteria"""
        EVALUATION_COUNT.labels(provider='unknown', status='started').inc()
        
        try:
            # Acquire rate limit token
            await self.rate_limiter.acquire()
            
            # Perform evaluation through circuit breaker
            result = await self.circuit_breaker.call(
                self._perform_evaluation,
                input_text, output_text, criteria
            )
            
            # Record successful evaluation
            EVALUATION_COUNT.labels(provider=result.provider, status='success').inc()
            EVALUATION_DURATION.labels(provider=result.provider).observe(1.0)  # This would be actual duration
            return result
            
        except Exception as e:
            self.logger.error("Evaluation failed", error=str(e))
            EVALUATION_COUNT.labels(provider='unknown', status='error').inc()
            raise EvaluationError(f"Failed to evaluate: {str(e)}")

    async def _perform_evaluation(self, input_text: str, output_text: str, criteria: str) -> EvaluationResult:
        """Internal evaluation logic"""
        provider = await self.provider_pool.get_available_provider()
        if not provider:
            raise ServiceUnavailable("No providers available")

        # Create evaluation prompt
        evaluation_prompt = self._create_evaluation_prompt(input_text, output_text, criteria)
        
        try:
            # Call LLM provider
            response = await provider.generate(evaluation_prompt)
            
            # Parse response
            result = self._parse_evaluation_response(response, provider.model_name)
            
            self.logger.info("Evaluation completed", provider=provider.model_name)
            return result
            
        except Exception as e:
            self.logger.error("Provider call failed", provider=provider.model_name, error=str(e))
            # Try next provider
            self.provider_pool.mark_provider_failed(provider)
            raise

    def _create_evaluation_prompt(self, input_text: str, output_text: str, criteria: str) -> str:
        """Create structured evaluation prompt"""
        return f"""You are an expert AI evaluator. Evaluate the following LLM output against the specified criteria.

INPUT TEXT:
{input_text}

OUTPUT TEXT:
{output_text}

EVALUATION CRITERIA:
{criteria}

Please evaluate the output and provide:
1. A detailed explanation of how well the output meets the criteria
2. A confidence score (0.0 to 1.0) indicating how certain you are of your evaluation
3. Individual scores for each relevant criterion mentioned (0.0 to 1.0 scale)

Consider these evaluation dimensions:
- Relevance: How well does the output address the input?
- Accuracy: Is the information provided correct and factual?
- Coherence: Is the output logically structured and consistent?
- Fluency: Is the language natural and well-formed?
- Completeness: Does the output fully address all aspects of the input?
- Instruction Following: Does the output follow any specific instructions given?
- Toxicity/Bias: Is the output free from harmful, toxic, or biased content?
- Hallucination: Does the output contain made-up or false information?
- Robustness: Would the output be appropriate across different contexts?

Respond in the following JSON format:
{{
    "explanation": "Detailed evaluation explanation",
    "confidence": 0.85,
    "criteria_scores": {{
        "relevance": 0.9,
        "accuracy": 0.8,
        "coherence": 0.85
    }}
}}"""

    def _parse_evaluation_response(self, response: str, provider_name: str) -> EvaluationResult:
        """Parse LLM evaluation response"""
        try:
            import json
            
            # Try to extract JSON from response
            start_idx = response.find('{')
            end_idx = response.rfind('}') + 1
            
            if start_idx == -1 or end_idx == 0:
                # Fallback parsing
                return EvaluationResult(
                    explanation=response.strip(),
                    confidence=0.5,
                    provider=provider_name
                )
            
            json_str = response[start_idx:end_idx]
            parsed = json.loads(json_str)
            
            return EvaluationResult(
                explanation=parsed.get("explanation", response.strip()),
                confidence=parsed.get("confidence"),
                provider=provider_name,
                criteria_scores=parsed.get("criteria_scores")
            )
            
        except Exception as e:
            self.logger.warning("Failed to parse evaluation response", error=str(e))
            return EvaluationResult(
                explanation=response.strip(),
                confidence=0.5,
                provider=provider_name
            )

    async def health_check(self) -> Dict[str, str]:
        """Check health of all components"""
        components = {}
        
        # Check Redis
        try:
            await self.rate_limiter.health_check()
            components["redis"] = "healthy"
        except Exception:
            components["redis"] = "unhealthy"
        
        # Check providers
        try:
            available_providers = await self.provider_pool.get_healthy_providers()
            if available_providers:
                components["providers"] = "healthy"
            else:
                components["providers"] = "unhealthy"
        except Exception:
            components["providers"] = "unhealthy"
        
        return components

# Dependency injection
_evaluation_engine = None

async def get_evaluation_engine() -> EvaluationEngine:
    """FastAPI dependency to get evaluation engine"""
    from main import evaluation_engine
    return evaluation_engine
