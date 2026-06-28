"""
ML Model Monitoring Metrics for Prometheus
Tracks model performance, success rates, and prediction quality
"""

from prometheus_client import Counter, Histogram, Gauge, Info
from typing import Dict, Any

# ================================================================
# ML Prediction Metrics
# ================================================================

# Counter: Total prediction requests by model type
ML_PREDICTION_COUNTER = Counter(
    'ml_predictions_total',
    'Total number of ML predictions made',
    ['model_type', 'status', 'vehicle_type', 'endpoint']
)

# Counter: Failed predictions by error type
ML_PREDICTION_ERRORS = Counter(
    'ml_prediction_errors_total',
    'Total number of ML prediction errors',
    ['model_type', 'error_type', 'vehicle_type']
)

# Histogram: Prediction latency in seconds
ML_PREDICTION_LATENCY = Histogram(
    'ml_prediction_latency_seconds',
    'ML prediction latency in seconds',
    ['model_type', 'status'],
    buckets=[0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0]
)

# Histogram: Prediction values (CTAT, VTAT)
ML_PREDICTION_VALUES = Histogram(
    'ml_prediction_values',
    'ML prediction values',
    ['model_type', 'metric_type'],
    buckets=[1, 2, 5, 10, 15, 20, 25, 30, 45, 60, 90, 120]
)

# Gauge: Model confidence scores
ML_MODEL_CONFIDENCE = Gauge(
    'ml_model_confidence',
    'Confidence score of ML model predictions',
    ['model_type', 'vehicle_type']
)

# Gauge: Model load status
ML_MODEL_LOAD_STATUS = Gauge(
    'ml_model_load_status',
    'ML model load status (1=loaded, 0=not loaded)',
    ['model_type']
)

# Gauge: Number of active predictions
ML_ACTIVE_PREDICTIONS = Gauge(
    'ml_active_predictions',
    'Number of active/pending ML predictions',
    ['model_type']
)

# Info: Model metadata
ML_MODEL_INFO = Info(
    'ml_model_info',
    'ML model metadata information',
    ['model_type']
)

# Counter: Route cache hits/misses
ML_CACHE_HITS = Counter(
    'ml_cache_hits_total',
    'ML route cache hits/misses',
    ['cache_type']  # hit, miss
)

# Histogram: Feature extraction time
ML_FEATURE_EXTRACTION_TIME = Histogram(
    'ml_feature_extraction_seconds',
    'Feature extraction latency in seconds',
    buckets=[0.001, 0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0]
)

# Gauge: Model performance metrics
ML_MODEL_PERFORMANCE = Gauge(
    'ml_model_performance',
    'Model performance metrics (MAE, RMSE, R2)',
    ['model_type', 'metric_name']
)

# ================================================================
# ML Prediction Response Model
# ================================================================

class MLPredictionMetrics:
    """Context manager for tracking ML prediction metrics"""
    
    def __init__(self, model_type: str, vehicle_type: str = "unknown", endpoint: str = "predict_ride"):
        self.model_type = model_type
        self.vehicle_type = vehicle_type
        self.endpoint = endpoint
        self.start_time = None
        self.status = "success"
        self.error_type = None
    
    def __enter__(self):
        import time
        self.start_time = time.time()
        ML_ACTIVE_PREDICTIONS.labels(model_type=self.model_type).inc()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        import time
        latency = time.time() - self.start_time
        ML_ACTIVE_PREDICTIONS.labels(model_type=self.model_type).dec()
        
        if exc_type is not None:
            self.status = "error"
            self.error_type = exc_type.__name__
            ML_PREDICTION_ERRORS.labels(
                model_type=self.model_type,
                error_type=self.error_type,
                vehicle_type=self.vehicle_type
            ).inc()
        
        ML_PREDICTION_COUNTER.labels(
            model_type=self.model_type,
            status=self.status,
            vehicle_type=self.vehicle_type,
            endpoint=self.endpoint
        ).inc()
        
        ML_PREDICTION_LATENCY.labels(
            model_type=self.model_type,
            status=self.status
        ).observe(latency)


def record_prediction_values(model_type: str, metric_type: str, value: float):
    """Record prediction values (CTAT, VTAT, etc.)"""
    ML_PREDICTION_VALUES.labels(
        model_type=model_type,
        metric_type=metric_type
    ).observe(value)

def record_cache_hit(cache_type: str):
    """Record cache hit or miss"""
    ML_CACHE_HITS.labels(cache_type=cache_type).inc()

def record_feature_extraction_time(duration: float):
    """Record feature extraction time"""
    ML_FEATURE_EXTRACTION_TIME.observe(duration)

def set_model_loaded(model_type: str, is_loaded: bool):
    """Set model load status"""
    ML_MODEL_LOAD_STATUS.labels(model_type=model_type).set(1 if is_loaded else 0)

def set_model_info(model_type: str, info: Dict[str, Any]):
    """Set model metadata"""
    ML_MODEL_INFO.labels(model_type=model_type).info(info)

def set_model_performance(model_type: str, metric_name: str, value: float):
    """Set model performance metric"""
    ML_MODEL_PERFORMANCE.labels(
        model_type=model_type,
        metric_name=metric_name
    ).set(value)