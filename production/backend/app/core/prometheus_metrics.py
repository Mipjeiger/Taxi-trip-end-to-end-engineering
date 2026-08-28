from prometheus_client import Counter, Histogram, Gauge, CollectorRegistry, Info
import logging

logger = logging.getLogger(__name__)

# Create registry
REGISTRY = CollectorRegistry()

# Existing metrics
REQUEST_COUNT = Counter('http_requests_total', 'Total HTTP requests', ['method', 'endpoint', 'status'], registry=REGISTRY)
REQUEST_LATENCY = Histogram('http_request_duration_seconds', 'HTTP request latency', ['method', 'endpoint'], registry=REGISTRY)
ACTIVE_RIDES = Gauge('active_rides', 'Number of active rides', registry=REGISTRY)
PREDICTION_TIME = Histogram('prediction_duration_seconds', 'Prediction latency', ['model_type'], registry=REGISTRY)

# ML Metrics (if not already defined)
try:
    ML_PREDICTION_COUNTER = Counter('ml_predictions_total', 'Total ML predictions', ['model_type', 'status', 'vehicle_type', 'endpoint'], registry=REGISTRY)
    ML_PREDICTION_ERRORS = Counter('ml_prediction_errors_total', 'Total ML prediction errors', ['model_type', 'error_type', 'vehicle_type'], registry=REGISTRY)
    ML_PREDICTION_LATENCY = Histogram('ml_prediction_latency_seconds', 'ML prediction latency', ['model_type', 'status'], registry=REGISTRY)
    ML_PREDICTION_VALUES = Histogram('ml_prediction_values', 'ML prediction values', ['model_type', 'metric_type'], registry=REGISTRY)
    ML_MODEL_CONFIDENCE = Gauge('ml_model_confidence', 'Model confidence scores', ['model_type', 'vehicle_type'], registry=REGISTRY)
    ML_MODEL_LOAD_STATUS = Gauge('ml_model_load_status', 'Model load status', ['model_type'], registry=REGISTRY)
    ML_ACTIVE_PREDICTIONS = Gauge('ml_active_predictions', 'Active ML predictions', ['model_type'], registry=REGISTRY)
    ML_MODEL_INFO = Info('ml_model_info', 'ML model metadata', ['model_type'], registry=REGISTRY)
    ML_CACHE_HITS = Counter('ml_cache_hits_total', 'Cache hits/misses', ['cache_type'], registry=REGISTRY)
    ML_FEATURE_EXTRACTION_TIME = Histogram('ml_feature_extraction_seconds', 'Feature extraction time', registry=REGISTRY)
    ML_MODEL_PERFORMANCE = Gauge('ml_model_performance', 'Model performance metrics', ['model_type', 'metric_name'], registry=REGISTRY)
    logger.info("✅ ML metrics registered successfully")
except Exception as e:
    logger.warning(f"⚠️ Some ML metrics already exist: {e}")