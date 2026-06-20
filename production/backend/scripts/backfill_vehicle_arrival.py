"""Backfill vehicle_arrival_at for historical trips using VTAT model.
Run this once after deploying new column in postgres database.
"""

import asyncio
import sys
import os
from pathlib import Path
from datetime import datetime, timedelta

# Add project root to path
current_file = Path(__file__).resolve()
backend_dir = Path(__file__).resolve().parent.parent
project_root = backend_dir.parent.parent # .../Gojek-Project/

# Add both backend directory and project root to path
sys.path.insert(0, str(backend_dir))
sys.path.insert(0, str(project_root))
print(f"📁 Backend directory: {backend_dir}")
print(f"📁 Project root: {project_root}")
print(f"📁 Python path includes: {sys.path[0]}")

from sqlalchemy import text
from app.core.postgres_db import get_postgres_db
from app.core.database import get_pg_db
from app.services.ml_predictor import MLPredictor
from app.models.trip import Trip
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def backfill_vehicle_arrival(batch_size: int = 500):
    """Backfill vehicle_arrival_at using VTAT model for all trips where it's null."""
    logger.info("🚀 Starting backfill process for vehicle_arrival_at using VTAT model")

    # Initialize ML predictor
    ml_predictor = MLPredictor()
    await ml_predictor.load_models()

    if not ml_predictor.is_loaded:
        logger.error("❌ Failed to load ML models. Aborting backfill.")
        return
    
    async for db in get_postgres_db():
        # Get all trips with NULL vehicle_arrival_at
        count_query = text("""
            SELECT COUNT(*)
            FROM analytics.trip
            WHERE vehicle_arrival_at IS NULL
                AND status = 'Completed'
                AND duration_minutes IS NOT NULL
                AND duration_minutes > 0
                AND pickup_location IS NOT NULL
                AND dropoff_location IS NOT NULL
        """)
        
        result = await db.execute(count_query)
        total_pending = result.scalar()

        if total_pending == 0:
            logger.info("✅ No trips found with NULL vehicle_arrival_at. Backfill complete.")
            return
        
        logger.info(f"🔍 Found {total_pending} trips with NULL vehicle_arrival_at. Processing in batches...")

        # Process in batches
        offset = 0
        updated_total = 0
        failed_total = 0

        while offset < total_pending:
            # Get batch of trips
            query = text("""
                SELECT ride_id, pickup_location, dropoff_location, ride_type,
                         distance_km, created_at, duration_minutes,
                         EXTRACT(HOUR FROM created_at) as hour,
                         EXTRACT(DOW FROM created_at) as day_of_week
                FROM analytics.trip
                WHERE vehicle_arrival_at IS NULL
                    AND status = 'Completed'
                    AND duration_minutes IS NOT NULL
                    AND duration_minutes > 0
                    AND pickup_location IS NOT NULL
                    AND dropoff_location IS NOT NULL
                ORDER BY created_at DESC
                LIMIT :limit OFFSET :offset
            """)

            result = await db.execute(query, {"limit": batch_size, "offset": offset})
            trips = result.fetchall()

            if not trips:
                break

            logger.info(f"⏳ Processing batch of {len(trips)} trips (offset {offset})")

            updated_batch = 0
            failed_batch = 0

            for trip in trips:
                try:
                    ride_id = trip[0]
                    pickup_location = trip[1]
                    dropoff_location = trip[2]
                    ride_type = trip[3] if trip[3] else "HRV"
                    distance_km = trip[4] if trip[4] else 10.0
                    created_at = trip[5]
                    if created_at is None:
                        created_at = datetime.now()
                    hour = int(trip[7]) if trip[7] is not None else created_at.hour
                    day_of_week = int(trip[8]) if trip[8] is not None else created_at.weekday()

                    # Get ML Prediction
                    prediction = await ml_predictor.predict_ride_metrics(
                        pickup=pickup_location,
                        drop=dropoff_location,
                        vehicle_type=ride_type,
                        hour=hour,
                        day_of_week=day_of_week,
                        distance_km=distance_km,
                        demand_pressure=500.0,  # Not used in VTAT prediction
                        rating_avg=4.5      # Not used in VTAT prediction
                    )

                    vtat_minutes = prediction.get('estimated_vehicle_arrival_minute')
                    
                    if vtat_minutes and vtat_minutes > 0:
                        vehicle_arrival_at = created_at + timedelta(minutes=vtat_minutes)

                        # Update trip record
                        update_query = text("""
                            UPDATE analytics.trip
                            SET vehicle_arrival_at = :vehicle_arrival_at
                            WHERE ride_id = :ride_id
                            AND vehicle_arrival_at IS NULL
                        """)

                        await db.execute(update_query, {
                            "vehicle_arrival_at": vehicle_arrival_at,
                            "ride_id": ride_id
                        })

                        updated_batch += 1
                        updated_total += 1
                    else:
                        logger.warning(f"⚠️ Invalid VTAT prediction for ride_id {ride_id}. Skipping update.")
                        failed_batch += 1
                        failed_total += 1

                except Exception as e:
                    logger.exception(f"❌ Failed to process ride_id {ride_id}. Error: {e}")
                    failed_batch += 1
                    failed_total += 1

            # Commit batch
            await db.commit()
            logger.info(f"✅ Batch completed: {updated_batch} updated, {failed_batch} failed.")
            logger.info(f"📊 Progress: {updated_total}/{total_pending} updated, {failed_total} failed.")

            offset += batch_size

        # Final verification
        verify_query = text("""
            SELECT COUNT(*) FROM analytics.trip
            WHERE vehicle_arrival_at IS NULL
            AND status = 'Completed'
        """)
        result = await db.execute(verify_query)
        remaining = result.scalar()

        logger.info(f"✅ Backfill complete!")
        logger.info(f"   - Updated: {updated_total}")
        logger.info(f"   - Failed: {failed_total}")
        logger.info(f"   - Remaining NULL: {remaining}")

if __name__ == "__main__":
    asyncio.run(backfill_vehicle_arrival(batch_size=500))