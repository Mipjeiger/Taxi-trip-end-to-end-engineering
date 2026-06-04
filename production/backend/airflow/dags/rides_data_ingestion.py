import logging
import os
import json
from pathlib import Path
from dotenv import load_dotenv
from datetime import datetime, timedelta

# Airflow imports
from airflow import DAG
from airflow.operators.python import PythonOperator
import pandas as pd

logger = logging.getLogger(__name__)

"""
Airflow DAG: Taxi Ride Data Ingestion Pipeline

Pipeline:
1. Extract parquet data
2. Transform + feature engineering
3. Load into PostgreSQL
4. Publish Kafka event
5. Run data quality checks

Architecture:
- PostgreSQL schema initialized externally from:
  production/backend/sql/init_postgres.sql
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
    description="Ingest ride data from Parquet to PostgreSQL with Kafka event streaming",
    schedule=None,  # Manual trigger
    catchup=False,
    tags=["taxi-trip", "postgres", "kafka"],
)

# ================================================================
# Constants
# ================================================================
PARQUET_PATH = os.getenv("PARQUET_PATH", "/opt/airflow/database/taxi_trip_engineering.parquet")
TEMP_DIR = "/tmp/airflow_taxi_pipeline"
os.makedirs(TEMP_DIR, exist_ok=True)

# Internal Docker PostgreSQL connection for Airflow tasks
def get_postgres_conn():
    """Get psycopg2 connection to internal PostgreSQL for Airflow tasks"""
    import psycopg2
    try:
        return psycopg2.connect(
            host=os.getenv("POSTGRES_HOST"),
            port=os.getenv("POSTGRES_PORT"),
            user=os.getenv("POSTGRES_USER"),
            password=os.getenv("POSTGRES_PASSWORD"),
            dbname=os.getenv("POSTGRES_DB"),
        )
    except Exception as e:
        logger.error(f"❌ Failed to connect to PostgreSQL: {e}")
        raise e

# ================================================================
# Task 1: Extract Data
# ================================================================

def extract_parquet_data(**context):
    """Extract taxi ride parquet data"""

    try:
        if not os.path.exists(PARQUET_PATH):
            raise FileNotFoundError(f"❌ Parquet file not found at {PARQUET_PATH}")

        df = pd.read_parquet(PARQUET_PATH)
        logger.info(f"✅ Extracted {len(df)} records | columns: {list(df.columns)}")

        # Normalize timestamps
        for col in df.columns:
            if pd.api.types.is_datetime64_any_dtype(df[col]):
                df[col] = pd.to_datetime(df[col]).dt.floor("us")

        extracted_path = os.path.join(
            TEMP_DIR,
            f"extracted_{datetime.now().strftime('%Y%m%d_%H%M%S')}.parquet",
        )
        df.to_parquet(extracted_path, 
                      index=False,
                      coerce_timestamps="us",
                      allow_truncated_timestamps=True,)

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
        extracted_path = context["task_instance"].xcom_pull(
            task_ids="extract_parquet",
            key="extracted_path",
        )

        if not extracted_path:
            raise ValueError("No extracted parquet path found in XCom")

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
            "user_id": "rider_id",
            "drop_location": "dropoff_location",
            "booking_id": "ride_id",
            "pickup_lon": "pickup_lng",
            "drop_lat": "dropoff_lat",
            "drop_lon": "dropoff_lng",
            "price": "actual_fare",
            "vehicle_type": "ride_type",
            "ride_distance": "distance_km",
            "estimated_drop_time_minute": "duration_minutes",
        }
        df = df.rename(columns={k: v for k, v in rename_map.items() if k in df.columns})

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

        # Fill status from booking_status if needed
        if "booking_status" in df.columns and "status" not in df.columns:
            df["status"] = df["booking_status"]

        # Add ingestion timestamp
        df["ingestion_timestamp"] = (datetime.now().isoformat())
        logger.info("✅ Data transformation completed")

        transformed_path = os.path.join(
            TEMP_DIR,
            f"transformed_{datetime.now().strftime('%Y%m%d_%H%M%S')}.parquet",
        )
        df.to_parquet(transformed_path, index=False)

        context["task_instance"].xcom_push(
            key="transformed_path",
            value=transformed_path,
        )
        logger.info(f"✅ Transformed {len(df)} rows | saved to {transformed_path}")

        return {
            "rows_transformed": len(df),
            "file_path": transformed_path,
            "timestamp": datetime.now().isoformat(),
        }

    except Exception as e:
        logger.exception("❌ Failed transforming data")
        raise e


# ================================================================
# Task 3: Load Into PostgreSQL (table: analytics.trip)
# ================================================================

def load_to_postgres(**context):
    """Load transformed data into PostgreSQL"""

    try:
        transformed_path = context["task_instance"].xcom_pull(
            task_ids="transform_data",
            key="transformed_path",
        )

        if not transformed_path:
            raise ValueError("No transformed parquet path found")

        df = pd.read_parquet(transformed_path)
        logger.info(f"✅ Loaded transformed dataframe with {len(df)} rows")

        # Map Dataframe columns to database schema (analytics.trip)
        trip_cols = [
            "ride_id", "rider_id", "driver_id", "pickup_location",
            "dropoff_location", "pickup_lat", "pickup_lng", "dropoff_lat",
            "dropoff_lng", "status", "ride_type", "actual_fare",
            "distance_km", "duration_minutes", "created_at", "completed_at"
        ]

        # Keep only columns that exist in df and trip schema
        insert_cols = [c for c in trip_cols if c in df.columns]
        df_insert = df[insert_cols].copy()

        # Cast types safely
        for float_col in ["pickup_lat", "pickup_lng", "dropoff_lat", "dropoff_lng",
                          "actual_fare", "distance_km", "duration_minutes"]:
            if float_col in df_insert.columns:
                df_insert[float_col] = pd.to_numeric(df_insert[float_col], errors="coerce")

        for ts_col in ["created_at", "completed_at"]:
            if ts_col in df_insert.columns:
                df_insert[ts_col] = pd.to_datetime(df_insert[ts_col], errors="coerce")

        # Upsert into PostgreSQL
        import psycopg2.extras

        conn = get_postgres_conn()
        inserted = 0

        try:
            with conn.cursor() as cur:
                for _, row in df_insert.iterrows():
                    cols = [c for c in insert_cols if pd.notna(row.get(c))]
                    vals = [row[c] for c in cols]
                    placeholders = ", ".join(["%s"] * len(cols))
                    col_names = ", ".join(cols)
                    
                    # ON CONFLICT DO UPDATE (upsert logic)
                    update_clause = ", ".join([
                        f"{c} = EXCLUDED.{c}" for c in cols if c != "ride_id"
                    ])

                    cur.execute(f"""
                        INSERT INTO analytics.trip ({col_names})
                        VALUES ({placeholders})
                        ON CONFLICT (ride_id) DO UPDATE SET {update_clause}
                    """, vals)
                    inserted += 1 # Count all processed rows as inserted for simplicity

            conn.commit()
            logger.info(f"✅ Loaded {inserted} records into PostgreSQL")

        finally:
            conn.close()

        context["task_instance"].xcom_push(
            key="rows_loaded",
            value=inserted,
        )

        return {
            "rows_loaded": inserted,
            "table": "analytics.trip",}

    except Exception as e:
        logger.exception("❌ Failed loading data into PostgreSQL")
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
            logger.warning("⚠️ confluent_kafka not installed")
            return {
                "event_published": False,
                "reason": "confluent_kafka missing",
            }

        load_result = context["task_instance"].xcom_pull(task_ids="load_to_postgres")

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
                "table": "analytics.trip",
                "database": "PostgreSQL (docker initiated)",
            },
        }

        producer.produce(
            topic="frontend-events",
            value=json.dumps(event).encode("utf-8"),
            callback=lambda err, msg: (
                logger.error(f"❌ Kafka delivery failed: {err}") if err 
                else logger.info(f"✅ Kafka event delivered to {msg.topic()} [{msg.partition()}] at offset {msg.offset()}")
            ),
        )
        producer.flush(timeout=10)
        return {"event_published": True}

    except Exception as e:
        logger.exception("❌ Failed publishing Kafka event")
        raise e

# ================================================================
# Task 5: Data Quality Checks
# ================================================================

def data_quality_checks(**context):
    """Run data quality validation againts the PostgreSQL database"""

    try:
        conn = get_postgres_conn()

        try:
            with conn.cursor() as cur:

                # Total rows
                cur.execute("SELECT COUNT(*) FROM analytics.trip;")
                total_rows = cur.fetchone()[0]
                logger.info(f"📊 Total rows in analytics.trip: {total_rows}")

                # Null checks
                cur.execute("""
                    SELECT
                        SUM(CASE WHEN ride_id IS NULL THEN 1 ELSE 0 END),
                        SUM(CASE WHEN rider_id IS NULL THEN 1 ELSE 0 END),
                        SUM(CASE WHEN driver_id IS NULL THEN 1 ELSE 0 END)
                    FROM analytics.trip;
                """)
                null_check = cur.fetchone()
                logger.info(f"✅ Nulls — ride_id: {null_check[0]}, rider_id: {null_check[1]}, driver_id: {null_check[2]}")

                # Invalid fares
                cur.execute("""
                    SELECT COUNT(*) FROM analytics.trip
                    WHERE actual_fare < 0 OR actual_fare IS NULL
                """)
                invalid_fares = cur.fetchone()[0]
                if invalid_fares > 0:
                    logger.warning(f"⚠️ Found {invalid_fares} records with invalid fares")
                else:
                    logger.info("✅ No invalid fares found")

                # Duplicates check
                cur.execute("""
                    SELECT COUNT(*) - COUNT(DISTINCT ride_id) FROM analytics.trip
                """)
                duplicates = cur.fetchone()[0]
                if duplicates > 0:
                    logger.warning(f"⚠️ Found {duplicates} duplicate ride_id records")
                else:
                    logger.info("✅ No duplicate ride_id records found")

                # Status distribution
                cur.execute("""
                    SELECT status, COUNT(*) FROM analytics.trip
                    GROUP BY status
                    ORDER BY COUNT(*) DESC
                """)
                status_dist = cur.fetchall()
                logger.info(f"📊 Ride status distribution: {status_dist}")
        
        finally:
            conn.close()

        return {
            "total_rows": total_rows,
            "invalid_fares": invalid_fares,
            "duplicates": duplicates,
            "data_quality_passed": invalid_fares == 0 and duplicates == 0,
            "timestamp": datetime.now().isoformat(),
        }

    except Exception as e:
        logger.exception("❌ Data quality checks failed")
        raise

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

task_load_postgres = PythonOperator(
    task_id="load_to_postgres",
    python_callable=load_to_postgres,
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

task_extract  >> task_transform >> task_load_postgres >> [task_kafka_event, task_quality_check]