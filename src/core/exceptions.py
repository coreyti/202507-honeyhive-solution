class EvaluationServiceException(Exception):
    """Base exception for evaluation service"""
    pass

class RateLimitExceeded(EvaluationServiceException):
    """Raised when rate limit is exceeded"""
    pass

class ServiceUnavailable(EvaluationServiceException):
    """Raised when service is unavailable"""
    pass

class EvaluationError(EvaluationServiceException):
    """Raised when evaluation fails"""
    pass

class CircuitBreakerOpen(EvaluationServiceException):
    """Raised when circuit breaker is open"""
    pass
