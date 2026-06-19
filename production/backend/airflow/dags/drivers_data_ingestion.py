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
           SELECT
                ride_type,
                driver_rating,
                COUNT(*) as trip_count,
                ROUND(COUNT(*) * 100.0 / SUM(COUNT(*)) OVER (PARTITION BY ride_type), 1) as percentage
            FROM analytics.trip
            WHERE driver_rating IS NOT NULL
                AND ride_type IS NOT NULL
                AND status = 'Completed'
            GROUP BY ride_type, driver_rating
            ORDER BY ride_type, driver_rating DESC
        """)
        rating_distribution = cursor.fetchall()
        
        if not rating_distribution: 
            logger.info(f"✅ All vehicle types already have drivers. Skipping.")
            conn.close()
            return {"status": "skipped", "count": count}
        
        # Clear existing drivers to start fresh
        logger.info("🧹 Clearing existing drivers table...")
        cursor.execute("TRUNCATE TABLE analytics.drivers CASCADE")
        conn.commit()

        # Track which vehicle types we've processed
        processed_types = set()
        driver_counter = 0
        
        # Create drivers based on rating distribution
        for row in rating_distribution:
            ride_type = row[0]
            rating = row[1]
            trip_count = row[2]
            percentage = row[3]

            # Dtermine how many drivers to create per rating
            if percentage >= 30: # Major rating (e.g. 4.2, 4.3)
                num_drivers = 2
            elif percentage >= 15: # Moderate rating (e.g., 4.6)
                num_drivers = 1
            else:
                num_drivers = 1  # Minor rating (e.g. 3.7, 4.9)
            
            # Ensure have at least 1 driver per vehicle type
            if ride_type not in processed_types:
                num_drivers = max(num_drivers, 1)

            # Create drivers for this rating
            for i in range(num_drivers):
                driver_counter += 1
                driver_id = f"DRV{str(driver_counter).zfill(3)}"

                # Generate realistic driver names
                first_names = ["Ahmad", "Budi", "Jaka", "Dedi", "Eka", "Fajar", "Gita", 
                               "Hendra", "Indah", "Joko", "Dedi", "Lukman", "Muhammad", 
                               "Nugroho", "Oscar", "Putra", "Rizki", "Zaki", "Taufik", "Wijaya"]
                
                last_names = ["Rizki", "Santoso", "Deni", "Firmansyah", "Putra", "Pratama", 
                              "Kusuma", "Wijaya", "Permata", "Susilo", "Satrio", "Hakim", 
                              "Angga", "Aji", "Setiawan", "Nugroho", "Hidayat", "Lesmana"]
            
                name = f"{random.choice(first_names)}{random.choice(last_names)}"

                # Generate plate number
                plate = f"B{random.randint(1000, 9999)}{random.choice(['AB', 'CD', 'EF', 'GH', 'IJ', 'KL', 'MN', 'OP', 'QR', 'ST', 'UV', 'WX', 'YZ'])}"

                # Generate random location near Jakarta (latitude and longitude)
                lat = -6.17 + (random.random() - 0.5) * 0.05
                lng = 106.82 + (random.random() - 0.5) * 0.05

                # Calculate total trips for the driver based on rating distribution
                total_trips = max(50, int(trip_count * (0.5 + random.random() * 0.5)))  # Randomize between 50% to 100% of trip_count

                # Insert driver into the database
                insert_query = """
                    INSERT INTO analytics.drivers (
                    driver_id, name, vehicle_type, plate,
                    rating, total_trips, status, lat, lng
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                """

                cursor.execute(insert_query, (
                    driver_id,
                    name,
                    ride_type,
                    plate,
                    rating,
                    total_trips,
                    'online',
                    lat,
                    lng
                ))
                logger.info(f"🚗 Created driver {driver_id} ({name}) for vehicle type {ride_type} with rating {rating}")

            processed_types.add(ride_type)
        
        conn.commit()
        logger.info(f"✅ Successfully populated drivers table with {driver_counter} drivers.")

        # Get final count
        cursor.execute("SELECT COUNT(*) FROM analytics.drivers")
        new_count = cursor.fetchone()[0]

        # Show distribution
        cursor.execute("""
            SELECT vehicle_type, COUNT(*) as count, AVG(rating) as avg_rating
            FROM analytics.drivers
            GROUP BY vehicle_type
            ORDER BY vehicle_type
        """)

        distribution = cursor.fetchall()
        logger.info("📊 Final drivers distribution:")

        for row in distribution:
            logger.info(f"Vehicle Type: {row[0]}, Count: {row[1]}, Avg Rating: {row[2]:.2f}")
        logger.info(f"📊 Total drivers after population: {new_count}")
        # Close connection
        conn.close()

        return {
            "status": "success",
            "new_count": new_count,
        }
    
    except Exception as e:
        logger.error(f"❌ Error populating drivers: {str(e)}")
        raise 

populate_task = PythonOperator(
    task_id="populate_drivers",
    python_callable=populate_drivers,
    dag=dag
)