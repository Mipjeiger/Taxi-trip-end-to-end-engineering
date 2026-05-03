from prometheus_client import Counter, Histogram, Gauge, CollectorRegistry

# Single registry for all metrics
REGISTRY = CollectorRegistry()

# Define Prometheus metrics
REQUEST_COUNT = Counter(
    'http_request_total',
    'Total HTTP requests',
    ['method', 'endpoint', 'status'],
    registry=REGISTRY
)

REQUEST_LATENCY = Histogram(
    'http_request_duration_seconds',
    'HTTP request latency',
    ['method', 'endpoint'],
    registry=REGISTRY
)

ACTIVE_RIDES = Gauge(
    'active_rides',
    'Number of active rides',
    registry=REGISTRY
)

PREDICTION_TIME = Histogram(
    'prediction_time_seconds',
    'Time to run a prediction',
    registry=REGISTRY
)