from fastapi import APIRouter, Response
from prometheus_client import generate_latest, CONTENT_TYPE_LATEST, Counter, Histogram, Gauge
import time

router = APIRouter()

# Define Prometheus metrics
REQUEST_COUNT = Counter('http_request_total', 'Total HTTP requests', ['method', 'endpoint', 'status'])
REQUEST_LATENCY = Histogram('http_request_duration_seconds', 'HTTP request latency', ['method', 'endpoint'])
ACTIVE_RIDES = Gauge('active_rides', 'Number of active rides')
PREDICTION_TIME = Histogram('prediction_time_seconds', 'Time to run a prediction')

@router.get("/metrics")
async def metrics():
    return Response(content=generate_latest(), media_type=CONTENT_TYPE_LATEST)