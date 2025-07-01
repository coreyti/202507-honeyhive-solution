from prometheus_client import Counter, Histogram, Gauge, Info

# Request metrics
REQUEST_COUNT = Counter(
    'llm_evaluation_requests_total',
    'Total number of evaluation requests',
    ['method', 'endpoint']
)

REQUEST_DURATION = Histogram(
    'llm_evaluation_request_duration_seconds',
    'Request duration in seconds',
    ['method', 'endpoint']
)

ERROR_COUNT = Counter(
    'llm_evaluation_errors_total',
    'Total number of errors',
    ['error_type']
)

# Evaluation metrics
EVALUATION_COUNT = Counter(
    'llm_evaluations_total',
    'Total number of evaluations performed',
    ['provider', 'status']
)

EVALUATION_DURATION = Histogram(
    'llm_evaluation_duration_seconds',
    'Evaluation duration in seconds',
    ['provider']
)

# Provider metrics
PROVIDER_HEALTH = Gauge(
    'llm_provider_health',
    'Provider health status (1=healthy, 0=unhealthy)',
    ['provider']
)

PROVIDER_REQUEST_COUNT = Counter(
    'llm_provider_requests_total',
    'Total requests to each provider',
    ['provider', 'status']
)

# System metrics
ACTIVE_CONNECTIONS = Gauge(
    'llm_evaluation_active_connections',
    'Number of active connections'
)

RATE_LIMIT_HITS = Counter(
    'llm_evaluation_rate_limit_hits_total',
    'Number of rate limit hits'
)

CIRCUIT_BREAKER_STATE = Gauge(
    'llm_evaluation_circuit_breaker_state',
    'Circuit breaker state (0=closed, 1=open, 2=half-open)'
)

# Application info
APP_INFO = Info(
    'llm_evaluation_service_info',
    'Application information'
)

def setup_metrics():
    """Initialize metrics with default values"""
    APP_INFO.info({
        'version': '1.0.0',
        'description': 'LLM Evaluation Service'
    })
