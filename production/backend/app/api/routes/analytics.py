from fastapi import APIRouter, Depends
from typing import Dict, Any
from datetime import datetime, timedelta
from app.core.database import AsyncSessionLocal
from sqlalchemy import func, select
from app.models.ride import Ride

router = APIRouter()

# Create endpoint router for analytics
@router.get("/metrics")
async def get_metrics() -> Dict[str, Any]:
    """return platform metrics for dashboard."""
    async with AsyncSessionLocal() as session:
        # Total rides in las 30 days
        thirty_days_ago = datetime.now() - timedelta(days=30)
        total_rides = await session.scalar(
            select(func.count(Ride.id)).where(Ride.created_at >= thirty_days_ago)
        ) or 0

        # Average time and price
        avg_time = await session.scalar(
            select(func.avg(Ride.estimated_time_min)).where(Ride.created_at >= thirty_days_ago)
        ) or 15.0

        avg_price = await session.scalar(
            select(func.avg(Ride.price)).where(Ride.created_at >= thirty_days_ago)
        ) or 50000.0

        # Active users (mok - replace with actual distinc customers)
        active_users = await session.scalar(
            select(func.count(func.distinct(Ride.user_id))).where(Ride.created_at >= thirty_days_ago)
        ) or 1500

    return {
        "total_rides": total_rides,
        "average_time_min": round(float(avg_time), 2),
        "average_price": round(float(avg_price)),
        "active_users": active_users
    }

@router.get("/route-popularity")
async def route_popularity(limit: int = 10):
    """Most popular routes"""
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(Ride.pickup_location, Ride.drop_location, func.count(Ride.id).label("count"))
            .group_by(Ride.pickup_location, Ride.drop_location)
            .order_by(func.count(Ride.id).desc())
            .limit(limit)
        )
        routes = [{"pickup": r[0], "drop": r[1], "count": r[2]} for r in result]
    
    return routes