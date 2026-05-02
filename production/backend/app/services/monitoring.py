import json
import numpy as np
from prometheus_client import Counter, Gauge, Histogram
from app.core.redis_client import get_redis
import redis.asyncio as redis

# Prometheus metrics
prediction_requests = Counter('prediction_requests_total', 'Total prediction requests')
prediction_latency = Histogram('prediction_latency_seconds', 'Prediction latency')
prediction_error = Counter('prediction_errors_total', 'Total prediction errors')

async def log_prediction_actual(ride_id: str, model_name: str, predicted_value: float, actual_value: float):
    """Store actual vs predicted for drift detection."""
    redis_client = await get_redis()
    key = f"drift:{model_name}"
    entry = json.dumps({
        "predicted": predicted_value,
        "actual": actual_value,
        "timestamp": __import__('time').time()
    })
    await redis_client.lpush(key, entry)
    await redis_client.ltrim(key, 0, 9990)  # Keep last

async def compute_psi(model_name: str) -> float:
    """Population stability index between expected and actual distributions."""
    redis_client = await get_redis()
    data = await redis_client.lrange(f"drift:{model_name}", 0, 999)
    if len(data) < 100:
        return 0.0  # Not enough data for PSI
    predictions = [json.loads(d)['predicted'] for d in data]
    actuals = [json.loads(d)['actual'] for d in data]

    # binning and PSI calculation
    bins = np.histogram_bin_edges(predictions, bins=10)
    expected = np.histogram(predictions, bins=bins)[0] / len(predictions)
    actual = np.histogram(actuals, bins=bins)[0] / len(actuals)
    psi = np.sum((actual - expected) * np.log((actual + 1e-6) / (expected + 1e-6)))
    return float(psi)