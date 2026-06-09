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
PARQUET_PATH = os.getenv("PARQUET_PATH", "/opt/airflow/database/taxi_trip_engineering_2.parquet")
TEMP_DIR = "/tmp/airflow_taxi_pipeline"
os.makedirs(TEMP_DIR, exist_ok=True)

# Row limit - to adjust fir many rows needed to be ingested for data in sql table
ROW_LIMIT = int(os.getenv("INGESTION_ROW_LIMIT", 15000))

# Parquet Source -> PostgreSQL table (analytics.trip) column mapping candidates
COLUMN_RENAME_MAP = {
    "booking_id": "ride_id",
    "customer_id": "rider_id",
    "drop_location": "dropoff_location",
    "vehicle_type": "ride_type",
    "booking_status": "booking_status",
    "ride_distance": "distance_km",
    "driver_ratings": "driver_rating",
    "estimated_drop_time_minute": "duration_minutes",
    "pickup_lon": "pickup_lng",
    "drop_lat": "dropoff_lat",
    "drop_lon": "dropoff_lng",
    "booking_value": "actual_fare",
}

# ----------------------------------------------------------------
# Separate statuses where NULL driver_status IS expected
# (no driver was ever assigned) vs. Completed (driver required).
# Only these statuses should have driver_status forced to NULL.
# "Completed" is intentionally excluded — completed rides MUST
# have a driver and should keep whatever driver_status they have.
# ----------------------------------------------------------------
NULL_DRIVER_STATUSES = [
    "Cancelled by Rider",
    "Cancelled by Driver",
    "No Driver Found",
    "Incomplete"
]

BOOKING_STATUSES = NULL_DRIVER_STATUSES + ["Completed"]

DRIVER_STATUSES = [
    "Online",
    "Offline"
]

# Internal Docker PostgreSQL connection for Airflow tasks
def get_postgres_conn():
    """Get psycopg2 connection to internal PostgreSQL for Airflow tasks"""
    import psycopg2
    try:
        return psycopg2.connect(
            host=os.getenv("POSTGRES_HOST_AIRFLOW"),
            port=os.getenv("POSTGRES_PORT_AIRFLOW"),
            user=os.getenv("POSTGRES_USER_AIRFLOW"),
            password=os.getenv("POSTGRES_PASSWORD_AIRFLOW"),
            dbname=os.getenv("POSTGRES_DB_AIRFLOW"),
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
        total_available = len(df)
        logger.info(f"✅ Extracted {len(df)} records | columns: {list(df.columns)}")

        # Apply row limit
        if len(df) > ROW_LIMIT:
            df = df.head(ROW_LIMIT)
            logger.info(f"⚠️ Row limit applied: ingesting {len(df)} of {total_available} available records")
        else:
            logger.info(f"✅ Extracting all {total_available} records (below row limit of {ROW_LIMIT})")

        logger.info(f"📊 Extracted columns: {df.columns.tolist()}")

        extracted_path = os.path.join(
            TEMP_DIR,
            f"extracted_{datetime.now().strftime('%Y%m%d_%H%M%S')}.parquet",
        )
        df.to_parquet(
                      extracted_path, 
                      index=False,
                      coerce_timestamps="us",
                      allow_truncated_timestamps=True,
        )

        # Push filepath only
        context["task_instance"].xcom_push(key="extracted_path", value=extracted_path)
        context["task_instance"].xcom_push(key="total_available", value=total_available)

        return {
            "rows_extracted": len(df),
            "total_available": total_available,
            "row_limit": ROW_LIMIT,
            "file_path": extracted_path,
        }

    except Exception as e:
        logger.exception("❌ Failed extracting parquet data")
        raise

# ================================================================
# Task 2: Transform Data
# ================================================================
def transform_data(**context):
    """Transform and feature engineer taxi ride data"""

    try:
        extracted_path = context["task_instance"].xcom_pull(
            task_ids="extract_parquet", key="extracted_path",
        )

        if not extracted_path:
            raise ValueError("No extracted parquet path found in XCom")

        df = pd.read_parquet(extracted_path)
        logger.info(f"✅ Loaded extracted dataframe with {len(df)} rows")

        # ========================================================
        # Standardize column names
        # ========================================================
        df.columns = (
            df.columns.str.lower() # lowercase for consistence fetch to sql table
            .str.strip()
            .str.replace(" ", "_")
            )
        logger.info(f"📊 Normalized column names: {df.columns.tolist()}")

        # ========================================================
        # Rename to match sql table schema
        # ========================================================
        df = df.rename(columns={
            k: v for k, v in COLUMN_RENAME_MAP.items() if k in df.columns
        })

        # ========================================================
        # EDA Features
        # ========================================================

        # Handle ride_id column standardization -> parquet uses "booking_id" -> "ride_id" in sql
        if "ride_id" not in df.columns:
            # try alternate names
            for alt in ["id", "trip_id"]:
                if alt in df.columns:
                    df["ride_id"] = df[alt]
                    logger.info(f"✅ Created ride_id column from {alt}")
                    break
            else:
                raise ValueError("No ride_id column found or created")
            
        # Handle rider_id column standardization -> parquet uses "customer_id" -> "rider_id" in sql
        if "rider_id" not in df.columns:
            for alt in ["user_id", "passenger_id"]:
                if alt in df.columns:
                    df["rider_id"] = df[alt]
                    logger.info(f"✅ Created rider_id column from {alt}")
                    break
            else:
                raise ValueError("No rider_id column found or created")
        
        # Proper feature driver status debugs
        if "booking_status" in df.columns:
            df["driver_status"] = df["booking_status"].apply(
                lambda s: "Online" if str(s).strip() == "Completed" else "Offline"
            )
            online_count = (df["driver_status"] == "Online").sum()
            offline_count = (df["driver_status"] == "Offline").sum()
            logger.info(f"✅ Mapped driver_status based on booking_status: Online={online_count}, Offline={offline_count}")
        else:
            df["driver_status"] = "Offline"
            logger.warning("⚠️ booking_status column not found, defaulting all driver_status to 'Offline'")
    
        # booking_status - keep as-is from source -- "booking_status" column maps directly to sql table (analytics.trip.booking_status)
        if "booking_status" in df.columns:
            df["status"] = df["booking_status"]
            logger.info("✅ Mapped booking_status to status column for SQL schema compatibility")
        elif "status" in df.columns:
            df["booking_status"] = df["status"]
        else:
            df["status"] = "Unknown"
            df["booking_status"] = "Unknown"
            logger.info("⚠️ No status column found, setting status and booking_status to 'Unknown'")

        # FIX 2: estimated_fare population + empty string cleaning
        # The source parquet stores missing fares as empty strings (""),
        # not NaN/None. pd.to_numeric(..., errors="coerce") converts ""
        # to NaN, which then becomes NULL in PostgreSQL — correct behaviour.
        if "actual_fare" not in df.columns and "price" in df.columns:
            df["actual_fare"] = pd.to_numeric(df["price"], errors="coerce")
            logger.info("✅ Created actual_fare column from price with numeric conversion")
        if "actual_fare" in df.columns:
            df["actual_fare"] = pd.to_numeric(df["actual_fare"], errors="coerce")

        # Resolve estimated_fare - always cast to numeric to clean empty strings and ensure correct type in SQL
        if "estimated_fare" in df.columns:
            df["estimated_fare"] = pd.to_numeric(df["estimated_fare"], errors="coerce")
            null_count = df["estimated_fare"].isna().sum()
            logger.info(f"✅ estimated_fare loaded from source column "
                f"({null_count} NaN after casting empty strings)"
                )
            # If all values are NaN after casting, fall back to actual_fare as estimated_fare
            if null_count == len(df):
                raise ValueError("All estimated_fare values are NaN after conversion - check source data for issues")
        else:
            estimated_fare_candidates = [
                "estimated_price",
                "fare_estimate",
                "predicted_fare",
                "estimate_fare",
            ]
            resolved = False
            for candidate in estimated_fare_candidates:
                if candidate in df.columns:
                    df["estimated_fare"] = pd.to_numeric(df[candidate], errors="coerce")
                    logger.info(f"✅ Created estimated_fare column from {candidate} with numeric conversion")
                    resolved = True
                    break

            if not resolved:
                # TODO: try for another column name
                try:
                    df["estimated_fare"] = df["estimated fare"]
                except KeyError:
                    logger.error("❌ No valid column found for estimated_fare")
                    df["estimated_fare"] = None
                    logger.warning("⚠️ Neither estimated_fare nor alternate columns found, setting estimated_fare to NULL")

        # Coordinate columns - parquet: pickup_lat, pickup_lon, drop_lat, drop_lon
        coord_map = {
            "pickup_lon": "pickup_lng",
            "drop_lat": "dropoff_lat",
            "drop_lon": "dropoff_lng",
        }
        for src, dst in coord_map.items():
            if src in df.columns and dst not in df.columns:
                df[dst] = df[src]

        # ========================================================
        # Validate required columns
        # ========================================================
        required_columns = ["ride_id","rider_id"]
        missing = [c for c in required_columns if c not in df.columns]
        if missing:
            raise ValueError(f"Required columns missing: {missing}")
        
        # ========================================================
        # Data cleaning
        # ========================================================
        before = len(df)
        df = df.drop_duplicates(subset=["ride_id"], keep="first")
        df = df.dropna(subset=["ride_id", "rider_id"])
        logger.info(f"✅ Cleaned data: dropped {before - len(df)} records with duplicate or null ride_id/rider_id")

        # ========================================================
        # Feature engineering
        # ========================================================
        if "distance_km" in df.columns and "duration_minutes" in df.columns:
            df["avg_speed_kmh"] = (df["distance_km"] / ((df["duration_minutes"] / 60) + 1e-6)).round(2)

        if "actual_fare" in df.columns and "distance_km" in df.columns:
            df["fare_per_km"] = (df["actual_fare"] / (df["distance_km"] + 1e-6)).round(2)

        df["ingestion_timestamp"] = datetime.now().isoformat()

        # Log null summary before saving
        key_cols = ["ride_id", "rider_id", "booking_status", "driver_status",
                    "status", "actual_fare", "distance_km"]
        null_summary = {c: int(df[c].isna().sum()) for c in key_cols if c in df.columns}
        logger.info(f"Null summary before saving:\n{null_summary}")

        transformed_path = os.path.join(TEMP_DIR, f"transformed_{datetime.now().strftime('%Y%m%d_%H%M%S')}.parquet")
        df.to_parquet(transformed_path, index=False)

        # Push transformed file path to XCom for downstream tasks
        context["task_instance"].xcom_push(key="transformed_path", value=transformed_path)
        logger.info(f"✅ Transformed data saved to {transformed_path} with {len(df)} records")
        return {"rows_transformed": len(df), "file_path": transformed_path}

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
            task_ids="transform_data", key="transformed_path",
        )

        if not transformed_path:
            raise ValueError("No transformed parquet path found")

        df = pd.read_parquet(transformed_path)
        logger.info(f"✅ Loading {len(df)} rows into sql table (analytics.trip)")

        # Columns matching the analytics.trip schema - we will only insert these columns and ignore any extras
        trip_cols = [
            "ride_id",
            "rider_id",
            "driver_status",
            "pickup_location",
            "dropoff_location",
            "pickup_lat",
            "pickup_lng",
            "dropoff_lat",
            "dropoff_lng",
            "status",
            "booking_status",
            "ride_type",
            "estimated_fare",
            "actual_fare",
            "distance_km",
            "duration_minutes",
            "driver_rating",
            "created_at",
            "completed_at",
        ]

        # Keep only columns that exist in df and trip schema
        insert_cols = [c for c in trip_cols if c in df.columns]
        df_insert = df[insert_cols].copy()
        logger.info(f"📊 Columns to insert: {insert_cols}")

        float_cols = [
            "pickup_lat", "pickup_lng", "dropoff_lat", "dropoff_lng",
            "actual_fare", "estimated_fare", "distance_km",
            "duration_minutes", "driver_rating"
        ]

        # Cast types safely
        for float_col in float_cols:
            if float_col in df_insert.columns:
                df_insert[float_col] = pd.to_numeric(df_insert[float_col], errors="coerce")

        for ts_col in ["created_at", "completed_at"]:
            if ts_col in df_insert.columns:
                df_insert[ts_col] = pd.to_datetime(df_insert[ts_col], errors="coerce")

        # Replace NaN with None for proper NULL insertion in PostgreSQL
        df_insert = df_insert.where(pd.notna(df_insert), None)

        logger.info(f"Database transformed: {df_insert.head()}")
        logger.info(f"Database types: {df_insert.dtypes}")

        # Upsert into PostgreSQL
        import psycopg2.extras

        conn = get_postgres_conn()
        inserted = 0
        skipped = 0

        try:
            with conn.cursor() as cur:
                for _, row in df_insert.iterrows():
                    # Only include non-None values in INSERT
                    cols = [c for c in insert_cols if row.get(c) is not None]
                    vals = [row[c] for c in cols]

                    if not cols:
                        skipped += 1
                        continue

                    placeholders = ", ".join(["%s"] * len(cols))
                    col_names = ", ".join(cols)
                    
                    # ON CONFLICT DO UPDATE (upsert logic)
                    update_clause = ", ".join([
                        f"{c} = EXCLUDED.{c}" for c in cols if c != "ride_id"
                    ])

                    # Read: sql table analytics.trip - inserting to columns
                    sql = f"""
                        INSERT INTO analytics.trip ({col_names})
                        VALUES ({placeholders})
                        ON CONFLICT (ride_id) 
                        DO UPDATE SET {update_clause}"""

                    cur.execute(sql, vals)
                    inserted += 1 # Count all processed rows as inserted for simplicity

            conn.commit()
            logger.info(f"✅ Loaded {inserted} records into PostgreSQL")
            logger.info(f"⚠️ Skipped {skipped} records with missing values")

        finally:
            conn.close()

        context["task_instance"].xcom_push(
            key="rows_loaded",value=inserted,
        )

        return {
            "rows_loaded": inserted,
            "table": "analytics.trip",}

    except Exception as e:
        logger.exception("❌ Failed loading data into PostgreSQL")
        raise

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
                "rows_loaded": load_result.get("rows_loaded", 0) if load_result else 0,
                "row_limit": ROW_LIMIT,
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

        # Validation checks
        total_rows = 0
        null_check = (0, 0, 0, 0)
        completed_missing_driver = 0
        invalid_fares = 0
        duplicates = 0

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
                        SUM(CASE WHEN estimated_fare IS NULL THEN 1 ELSE 0 END),
                        SUM(CASE WHEN booking_status IS NULL THEN 1 ELSE 0 END)
                    FROM analytics.trip;
                """)
                null_check = cur.fetchone()
                logger.info(f"✅ Nulls — ride_id: {null_check[0]}, rider_id: {null_check[1]}, estimated_fare: {null_check[2]}, booking_status: {null_check[3]}")

                # --- Driver Status null breakdown by status --
                cur.execute("""
                    SELECT
                        booking_status,
                        COUNT(*) AS total,
                        SUM(CASE WHEN driver_status IS NULL THEN 1 ELSE 0 END) AS null_driver,
                        ROUND(100.0 * SUM(CASE WHEN driver_status IS NULL THEN 1 ELSE 0 END) / NULLIF(COUNT(*), 0), 2) AS null_driver_pct
                    FROM analytics.trip
                    GROUP BY booking_status
                    ORDER BY total DESC;
                """)
                driver_by_status = cur.fetchall()
                logger.info("📊 Driver Status null breakdown by status:")
                for row in driver_by_status:
                    logger.info(f"   Status: {row[0]}, Total: {row[1]}, Null Driver Status: {row[2]}, Null Driver Status %: {row[3]}%")

                # Only flag as problem if COMPLETED rides have null driver_status
                cur.execute("""
                    SELECT COUNT(*) 
                    FROM analytics.trip
                    WHERE booking_status = 'Completed' 
                    AND driver_status IS NULL;
                """)
                completed_missing_driver = cur.fetchone()[0]
                if completed_missing_driver > 0:
                    logger.warning(f"⚠️ Found {completed_missing_driver} completed rides with missing driver_status")
                else:
                    logger.info("✅ No completed rides with missing driver_status found")

                # Invalid fares
                cur.execute("""
                    SELECT COUNT(*) 
                    FROM analytics.trip
                    WHERE actual_fare < 0 OR actual_fare IS NULL;
                """)
                invalid_fares = cur.fetchone()[0]
                if invalid_fares > 0:
                    logger.warning(f"⚠️ Found {invalid_fares} records with invalid fares")
                else:
                    logger.info("✅ No invalid fares found")

                # Duplicates check
                cur.execute("""
                    SELECT COUNT(*) - COUNT(DISTINCT ride_id) FROM analytics.trip;
                """)
                duplicates = cur.fetchone()[0]
                if duplicates > 0:
                    logger.warning(f"⚠️ Found {duplicates} duplicate ride_id records")
                else:
                    logger.info("✅ No duplicate ride_id records found")

                # Status distribution
                cur.execute("""
                    SELECT booking_status, 
                    COUNT(*) FROM analytics.trip
                    GROUP BY booking_status
                    ORDER BY COUNT(*) DESC;
                """)
                status_dist = cur.fetchall()
                logger.info(f"📊 Ride status distribution: {status_dist}")

                # estimated_fare null breakdown by booking_status
                cur.execute("""
                    SELECT
                            booking_status,
                            COUNT(*) AS total,
                            SUM(CASE WHEN estimated_fare IS NULL THEN 1 ELSE 0 END) AS null_estimated_fare
                            FROM analytics.trip
                            GROUP BY booking_status
                            ORDER BY total DESC;
                            """)
                fare_nulls_by_status = cur.fetchall()
                logger.info("📊 Estimated fare null breakdown by booking_status:")
                for row in fare_nulls_by_status:
                    logger.info(f"   Status: {row[0]}, Total: {row[1]}, Null Estimated Fare: {row[2]}")

        finally:
            conn.close()

        # for null is EXPECTED - are non-Completed rides -- Only fail if Completed rides are missing driver_status
        data_quality_passed = (
            invalid_fares == 0
            and duplicates == 0
            and completed_missing_driver == 0
        )
        logger.info(
            f"{'✅' if data_quality_passed else '❌'}"
            f"Data quality: {'PASSED' if data_quality_passed else 'FAILED'} | "
        )

        return {
            "total_rows": total_rows,
            "row_limit": ROW_LIMIT,
            "null_ride_id": null_check[0],
            "null_rider_id": null_check[1],
            "null_driver_status": null_check[2],
            "null_booking_status": null_check[3],
            "completed_missing_driver_status": completed_missing_driver,
            "invalid_fares": invalid_fares,
            "duplicates": duplicates,
            "data_quality_passed": data_quality_passed,
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