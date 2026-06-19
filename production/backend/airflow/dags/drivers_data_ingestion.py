import logging
import os
from pathlib import Path
from dotenv import load_dotenv
from datetime import datetime, timedelta
import random

# Airflow imports
from airflow import DAG
from airflow.operators.python import PythonOperator
import pandas as pd
import psycopg2

logger = logging.getLogger(__name__)

BASE_DIR = Path(__file__).resolve().parent.parent.parent
ENV_PATH = BASE_DIR / ".env"

if not ENV_PATH.exists():
    ENV_PATH = BASE_DIR.parent / ".env"

load_dotenv(dotenv_path=ENV_PATH)

"""Drivers data ingestion for retrieving drivers database from Airflow to PostgreSQL database"""
default_args = {
    "owner": "taxi-trip-team",
    "depends_on_past": False,
    "retries": 2,
    "retry_delay": timedelta(minutes=4),
    "start_date": datetime(2026, 1, 1),
    "email_on_failure": False,
    "email_on_retry": False,
}

dag = DAG(
    dag_id="drivers_data_ingestion",
    default_args=default_args,
    description="Populate drivers table from trip data for driver matching",
    schedule=None,  # Manual trigger only
    catchup=False,
    tags=["taxi-trip", "postgres", "drivers"],
    is_paused_upon_creation=False,
    max_active_runs=1,
    max_active_tasks=1,
)

def get_postgres_conn():
    """Get psycopg2 connection to PostgreSQL database"""
    try:
        return psycopg2.connect(
            host=os.getenv("POSTGRES_HOST_AIRFLOW"),
            port=os.getenv("POSTGRES_PORT_AIRFLOW"),
            user=os.getenv("POSTGRES_USER_AIRFLOW"),
            password=os.getenv("POSTGRES_PASSWORD_AIRFLOW"),
            dbname=os.getenv("POSTGRES_DB_AIRFLOW"),
        )
    
    except Exception as e:
        logger.error(f"Failed to connect to PostgreSQL: {str(e)}")
        raise e
    
def populate_drivers(**context):
    """Populate drivers table from trip data - Fixed version"""
    try:
        conn = get_postgres_conn()
        cursor = conn.cursor()

        # Check current count
        cursor.execute("SELECT COUNT(*) FROM analytics.drivers")
        count = cursor.fetchone()[0]
        
        logger.info(f"📊 Current drivers count: {count}")

        # Check which vehicle types are missing
        cursor.execute("""
            SELECT DISTINCT ride_type 
            FROM analytics.trip 
            WHERE driver_rating IS NOT NULL 
              AND ride_type IS NOT NULL 
              AND status = 'Completed'
              AND ride_type NOT IN (
                  SELECT DISTINCT vehicle_type FROM analytics.drivers
              )
        """)
        missing_types = cursor.fetchall()
        
        if not missing_types:
            logger.info(f"✅ All vehicle types already have drivers. Skipping.")
            conn.close()
            return {"status": "skipped", "count": count}
        
        logger.info(f"📊 Missing vehicle types: {[row[0] for row in missing_types]}")
        
        # Generate drivers ONLY for missing vehicle types
        for row in missing_types:
            vehicle_type = row[0]
            logger.info(f"🔄 Creating driver for vehicle type: {vehicle_type}")
            
            # Check if this vehicle type already has a driver
            cursor.execute(
                "SELECT COUNT(*) FROM analytics.drivers WHERE vehicle_type = %s",
                (vehicle_type,)
            )
            exists = cursor.fetchone()[0]
            
            if exists > 0:
                logger.info(f"✅ Driver for {vehicle_type} already exists. Skipping.")
                continue
            
            # Insert driver for this vehicle type
            query = """
            INSERT INTO analytics.drivers (driver_id, name, vehicle_type, plate,
                rating, total_trips, status, lat, lng)
            SELECT
                CONCAT('DRV', LPAD((
                    SELECT COALESCE(MAX(CAST(SUBSTRING(driver_id, 4) AS INTEGER)), 0) + 1
                    FROM analytics.drivers
                )::TEXT, 3, '0')) as driver_id,
                CONCAT('Driver ', %(vehicle_type)s) as name,
                %(vehicle_type)s as vehicle_type,
                CONCAT('B ',
                        LPAD(FLOOR(RANDOM() * 10000)::TEXT, 4, '0'),
                        ' ',
                        CHR(65 + FLOOR(RANDOM() * 26)::INT),
                        CHR(65 + FLOOR(RANDOM() * 26)::INT)) as plate,
                ROUND(AVG(driver_rating)::NUMERIC, 1) as rating,
                COUNT(*) as total_trips,
                'online' as status,
                -6.17 + (RANDOM() - 0.5) * 0.05 as lat,
                106.82 + (RANDOM() - 0.5) * 0.05 as lng
            FROM analytics.trip
            WHERE driver_rating IS NOT NULL
                AND ride_type = %(vehicle_type)s
                AND status = 'Completed'
            GROUP BY ride_type
            """

            cursor.execute(query, {"vehicle_type": vehicle_type})
            conn.commit()
            
            logger.info(f"✅ Created driver for {vehicle_type}")

        # Get final count
        cursor.execute("SELECT COUNT(*) FROM analytics.drivers")
        new_count = cursor.fetchone()[0]

        logger.info(f"✅ Drivers table now has {new_count} records.")
        conn.close()

        return {"status": "success", "new_count": new_count}
    
    except Exception as e:
        logger.error(f"Failed to populate drivers table: {str(e)}")
        raise

populate_task = PythonOperator(
    task_id="populate_drivers",
    python_callable=populate_drivers,
    dag=dag
)