from pydantic import BaseModel, Field, validator
from typing import Optional, Dict, Any
from enum import Enum

class EvaluationCriteria(str, Enum):
    RELEVANCE = "relevance"
    ACCURACY = "accuracy"
    COHERENCE = "coherence"
    FLUENCY = "fluency"
    COMPLETENESS = "completeness"
    INSTRUCTION_FOLLOWING = "instruction_following"
    TOXICITY_BIAS = "toxicity_bias"
    HALLUCINATION = "hallucination"
    ROBUSTNESS = "robustness"

class EvaluationRequest(BaseModel):
    input: str = Field(..., min_length=1, max_length=1048576, description="Input text to evaluate")
    output: str = Field(..., min_length=1, max_length=1048576, description="Output text to evaluate")
    criteria: str = Field(..., min_length=1, max_length=1048576, description="Evaluation criteria")
    
    @validator('input', 'output', 'criteria')
    def validate_size(cls, v):
        if len(v.encode('utf-8')) < 1024:
            raise ValueError('Payload must be at least 1KB')
        if len(v.encode('utf-8')) > 1048576:
            raise ValueError('Payload must not exceed 1MB')
        return v

class EvaluationResponse(BaseModel):
    success: bool
    explanation: str
    confidence: Optional[float] = None
    evaluation_time_ms: Optional[int] = None
    provider: Optional[str] = None
    criteria_scores: Optional[Dict[str, float]] = None

class ErrorResponse(BaseModel):
    success: bool = False
    explanation: str
    error_code: str
    retry_after: Optional[int] = None

class HealthResponse(BaseModel):
    status: str
    timestamp: str
    version: str = "1.0.0"
    components: Optional[Dict[str, str]] = None
