from fastapi import APIRouter
from fastapi.responses import Response
from prometheus_client import generate_latest, CONTENT_TYPE_LATEST
from app.core.prometheus_metrics import REGISTRY

router = APIRouter()

# Router prometheus metrics endpoint
@router.get("/metrics")
async def metrics():
    return Response(content=generate_latest(REGISTRY), media_type=CONTENT_TYPE_LATEST)