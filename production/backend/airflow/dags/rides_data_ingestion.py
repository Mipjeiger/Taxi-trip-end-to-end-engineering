import logging
import os
import json
from pathlib import Path
from dotenv import load_dotenv
from datetime import datetime, timedelta

# Airflow imports
from airflow import DAG
from airflow.operators.python import PythonOperator

# Data processing imports
import pandas as pd

logger = logging.getLogger(__name__)

"""
Airflow DAG: Taxi Ride Data Ingestion Pipeline

Pipeline:
1. Extract parquet data
2. Transform + feature engineering
3. Load into DuckDB
4. Publish Kafka event
5. Run data quality checks

Architecture:
- DuckDB schema initialized externally from:
  production/backend/sql/init_duckdb.sql
- Airflow handles orchestration only
"""

# ================================================================
# Load Environment Variables
# ================================================================

BASE_DIR = Path(__file__).resolve().parent.parent.parent
ENV_PATH = BASE_DIR / ".env"

if not ENV_PATH.exists():
    ENV_PATH = BASE_DIR.parent / ".env"

load_dotenv(dotenv_path=ENV_PATH)

# ================================================================
# DAG Configuration
# ================================================================

default_args = {
    "owner": "taxi-trip-team",
    "depends_on_past": False,
    "retries": 2,
    "retry_delay": timedelta(minutes=5),
    "start_date": datetime(2026, 1, 1),
    "email_on_failure": False,
    "email_on_retry": False,
}

dag = DAG(
    dag_id="rides_data_ingestion",
    default_args=default_args,
    description="Ingest ride data from Parquet to DuckDB with Kafka event streaming",
    schedule=None,  # Manual trigger
    catchup=False,
    tags=["taxi-trip", "duckdb", "kafka"],
)

# ================================================================
# Constants
# ================================================================

PARQUET_PATH = os.getenv("PARQUET_PATH", "/backend/database/taxi_trip_engineering.parquet")
TEMP_DIR = "/tmp/airflow_taxi_pipeline"
os.makedirs(TEMP_DIR, exist_ok=True)

# ================================================================
# Task 1: Extract Data
# ================================================================

def extract_parquet_data(**context):
    """Extract taxi ride parquet data"""

    try:
        if not os.path.exists(PARQUET_PATH):
            raise ValueError(f"❌ Parquet file not found at {PARQUET_PATH}")

        df = pd.read_parquet(PARQUET_PATH)

        logger.info(f"✅ Extracted {len(df)} records from parquet")
        logger.info(f"📊 Columns: {list(df.columns)}")

        extracted_path = os.path.join(
            TEMP_DIR,
            f"extracted_{datetime.now().strftime('%Y%m%d_%H%M%S')}.parquet",
        )
        df.to_parquet(extracted_path, index=False)

        # Push filepath only
        context["task_instance"].xcom_push(
            key="extracted_path",
            value=extracted_path,
        )

        return {
            "rows_extracted": len(df),
            "file_path": extracted_path,
            "timestamp": datetime.now().isoformat(),
        }

    except Exception as e:
        logger.exception("❌ Failed extracting parquet data")
        raise e


# ================================================================
# Task 2: Transform Data
# ================================================================

def transform_data(**context):
    """Transform and feature engineer taxi ride data"""

    try:
        task_instance = context["task_instance"]
        extracted_path = task_instance.xcom_pull(
            task_ids="extract_parquet",
            key="extracted_path",
        )

        if not extracted_path:
            raise ValueError(
                "No extracted parquet path found in XCom"
            )

        df = pd.read_parquet(extracted_path)
        logger.info(f"✅ Loaded extracted dataframe with {len(df)} rows")

        # ========================================================
        # Standardize column names
        # ========================================================
        df.columns = (
            df.columns.str.lower()
            .str.strip()
            .str.replace(" ", "_")
            )

        # Rename supabase columns -> Duckdb trip schema
        rename_map = {
            "id": "ride_id",
            "user_id": "rider_id",
            "drop_location": "dropoff_location",
        }
        df = df.rename(columns={
            k: v for k, v in rename_map.items() if k in df.columns
        })

        # ========================================================
        # Validate required columns
        # ========================================================
        required_columns = ["ride_id","rider_id"]
        for col in required_columns:
            if col not in df.columns:
                raise ValueError(f"Required column missing: {col}")

        # ========================================================
        # Data Cleaning
        # ========================================================
        df = df.drop_duplicates(subset=["ride_id"], keep="first",)
        df = df.dropna(subset=["ride_id", "rider_id"])

        # ========================================================
        # Feature Engineering
        # ========================================================

        if ("distance_km" in df.columns and "duration_minutes" in df.columns):
            df["avg_speed"] = (df["distance_km"] / ((df["duration_minutes"] / 60) + 1e-6))

        if ("actual_fare" in df.columns and "distance_km" in df.columns):
            df["fare_per_km"] = (df["actual_fare"] / (df["distance_km"] + 1e-6))

        # Add ingestion timestamp
        df["ingestion_timestamp"] = (datetime.now().isoformat())
        logger.info("✅ Data transformation completed")

        transformed_path = os.path.join(
            TEMP_DIR,
            f"transformed_{datetime.now().strftime('%Y%m%d_%H%M%S')}.parquet",
        )
        df.to_parquet(transformed_path, index=False)

        task_instance.xcom_push(
            key="transformed_path",
            value=transformed_path,
        )

        return {
            "rows_transformed": len(df),
            "file_path": transformed_path,
            "timestamp": datetime.now().isoformat(),
        }

    except Exception as e:
        logger.exception("❌ Failed transforming data")
        raise e


# ================================================================
# Task 3: Load Into DuckDB
# ================================================================

def load_to_duckdb(**context):
    """Load transformed data into DuckDB"""

    try:
        import duckdb

        task_instance = context["task_instance"]
        transformed_path = task_instance.xcom_pull(
            task_ids="transform_data",
            key="transformed_path",
        )

        if not transformed_path:
            raise ValueError(
                "No transformed parquet path found"
            )

        df = pd.read_parquet(transformed_path)
        logger.info(f"✅ Loaded transformed dataframe with {len(df)} rows")

        duckdb_path = os.getenv("DUCKDB_PATH")

        if not duckdb_path:
            raise ValueError("DUCKDB_PATH environment variable not set")
        
        # ========================================================
        # Use context manager so lock is released immediately after write
        # ========================================================
        with duckdb.connect(duckdb_path) as conn:
            conn.register("temp_rides_df", df)

            conn.execute(
                """
                INSERT OR REPLACE INTO trip (
                    ride_id,
                    rider_id,
                    driver_id,
                    pickup_location,
                    dropoff_location,
                    pickup_lat,
                    pickup_lng,
                    dropoff_lat,
                    dropoff_lng,
                    status,
                    ride_type,
                    estimated_fare,
                    actual_fare,
                    distance_km,
                    duration_minutes,
                    created_at,
                    completed_at
                )
                SELECT
                    ride_id,
                    rider_id,
                    CAST(driver_id AS VARCHAR),
                    pickup_location,
                    dropoff_location,
                    TRY_CAST(pickup_lat AS DOUBLE),
                    TRY_CAST(pickup_lon AS DOUBLE),
                    TRY_CAST(drop_lat AS DOUBLE),
                    TRY_CAST(drop_lon AS DOUBLE),
                    COALESCE(booking_status, status, 'unknown'),
                    vehicle_type,
                    TRY_CAST(price AS DOUBLE),
                    TRY_CAST(price AS DOUBLE),
                    TRY_CAST(ride_distance AS DOUBLE),
                    TRY_CAST(estimated_drop_time_minute AS DOUBLE),
                    TRY_CAST(created_at AS TIMESTAMP),
                    TRY_CAST(completed_at AS TIMESTAMP)
                FROM temp_rides_df
                WHERE ride_id IS NOT NULL
                    AND ride_id IS NOT NULL
            """)

            inserted_rows = conn.execute("SELECT COUNT(*) FROM trip").fetchone()[0]
            logger.info(f"✅ Inserted {inserted_rows} rows into ride table")

            task_instance.xcom_push(
                key="rows_loaded",
                value=inserted_rows,
            )

            return {
                "rows_loaded": inserted_rows,
                "table": "ride",
                "timestamp": datetime.now().isoformat(),
            }

    except Exception as e:
        logger.exception("❌ Failed loading data into DuckDB")
        raise e

# ================================================================
# Task 4: Publish Kafka Event
# ================================================================

def publish_kafka_event(**context):
    """Publish ingestion completion event to Kafka"""

    try:
        try:
            from confluent_kafka import Producer
        except ImportError:
            logger.warning(
                "⚠️ confluent_kafka not installed"
            )
            return {
                "event_published": False,
                "reason": "confluent_kafka missing",
            }

        task_instance = context["task_instance"]
        load_result = task_instance.xcom_pull(
            task_ids="load_to_duckdb"
        )

        # -- User intenal listener port ---
        bootstrap_servers = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "kafka:9092",)

        producer = Producer({
            "bootstrap.servers": bootstrap_servers,
            "client.id": "airflow-producer",
            "socket.timeout.ms": 10000,
            "message.timeout.ms": 10000,
        })

        event = {
            "event_type": "data_ingestion_complete",
            "pipeline": "rides_data_ingestion",
            "event_timestamp": datetime.now().isoformat(),
            "event_data": {
                "rows_loaded": load_result.get("rows_loaded") if load_result else 0,
                "table": "trip",
                "duckdb_path": os.getenv("DUCKDB_PATH"),
            },
        }

        producer.produce(
            topic="frontend-events",
            value=json.dumps(event).encode("utf-8"),
            callback=lambda err, msg: (
                logger.error(f"❌ Kafka delivery failed: {err}") if err else 
                logger.info(f"✅ Kafka event delivered to {msg.topic()} [{msg.partition()}] at offset {msg.offset()}")
            ),
        )
        producer.flush(timeout=10)

        logger.info("✅ Kafka event published successfully")
        return {
            "event_published": True,
            "timestamp": datetime.now().isoformat(),
        }

    except Exception as e:
        logger.exception("❌ Failed publishing Kafka event")
        raise e


# ================================================================
# Task 5: Data Quality Checks
# ================================================================

def data_quality_checks(**context):
    """Run DuckDB data quality validation"""

    try:
        import duckdb

        duckdb_path = os.getenv("DUCKDB_PATH")
        if not duckdb_path:
            raise ValueError("DUCKDB_PATH environment variable not set")

        with duckdb.connect(duckdb_path) as conn:

            # ========================================================
            # Total Rows Check
            # ========================================================

            total_rows = conn.execute("SELECT COUNT(*) FROM ride").fetchone()[0]
            logger.info(f"✅ Total rides rows: {total_rows}")

            # ========================================================
            # Row count
            # ========================================================
            total_rows = conn.execute("SELECT COUNT(*) FROM trip").fetchone()[0]
            logger.info(f"✅ Total trip rows: {total_rows}")

            # ========================================================
            # Null Checks
            # ========================================================
            null_check = conn.execute(
                """
                SELECT
                    SUM(CASE WHEN ride_id IS NULL THEN 1 ELSE 0 END) AS null_ride_id,
                    SUM(CASE WHEN rider_id IS NULL THEN 1 ELSE 0 END) AS null_rider_id,
                    SUM(CASE WHEN driver_id IS NULL THEN 1 ELSE 0 END) AS null_driver_id
                FROM ride
                """
            ).fetchone()

            logger.info(
                f"""
                ✅ Null Checks:
                - ride_id: {null_check[0]}
                - rider_id: {null_check[1]}
                - driver_id: {null_check[2]}
                """
            )

            # ========================================================
            # Fare Validation
            # ========================================================

            invalid_fares = conn.execute(
                """
                SELECT COUNT(*)
                FROM trip
                WHERE actual_fare < 0
                OR actual_fare IS NULL
                """
            ).fetchone()[0]

            if invalid_fares > 0:
                logger.warning(f"⚠️ Found {invalid_fares} invalid fares")
            else:
                logger.info("✅ All fares valid")

            # Duplicate check
            duplicates = conn.execute("""SELECT COUNT(*) - COUNT(DISTINCE ride_id)
                                      FROM trip""").fetchone()[0]
            if duplicates > 0:
                logger.warning(f"⚠️ Found {duplicates} duplicate ride_id entries")
            else:
                logger.info("✅ No duplicate ride_id entries found")

            # Status distribution check
            status_dist = conn.execute("""
                SELECT status, COUNT(*) AS cnt
                FROM trip
                GROUP BY status
                ORDER BY cnt DESC
                """).fetchall()
            logger.info(f"📊 Status Distribution: {status_dist}")

        return {
            "total_rows": total_rows,
            "invalid_fares": invalid_fares,
            "duplicates": duplicates,
            "data_quality_passed": invalid_fares == 0 and duplicates == 0,
            "timestamp": datetime.now().isoformat(),
        }

    except Exception as e:
        logger.exception("❌ Data quality checks failed")
        raise e

# ================================================================
# Airflow Task Operators
# ================================================================

task_extract = PythonOperator(
    task_id="extract_parquet",
    python_callable=extract_parquet_data,
    dag=dag,
)

task_transform = PythonOperator(
    task_id="transform_data",
    python_callable=transform_data,
    dag=dag,
)

task_load_duckdb = PythonOperator(
    task_id="load_to_duckdb",
    python_callable=load_to_duckdb,
    dag=dag,
)

task_kafka_event = PythonOperator(
    task_id="publish_kafka_event",
    python_callable=publish_kafka_event,
    dag=dag,
)

task_quality_check = PythonOperator(
    task_id="data_quality_checks",
    python_callable=data_quality_checks,
    dag=dag,
)

# ================================================================
# Task Dependencies
# ================================================================

task_extract  >> task_transform >> task_load_duckdb >> [task_kafka_event, task_quality_check]