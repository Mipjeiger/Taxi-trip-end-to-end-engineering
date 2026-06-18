import logging
import os
import redis
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
4. Cache route features to Redis
5. Warm Redis cache for popular routes
6. Publish Kafka event
7. Run data quality checks
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
    description="Ingest ride data from Parquet to PostgreSQL with Redis caching",
    schedule=None,  # Manual trigger
    catchup=False,
    tags=["taxi-trip", "postgres", "redis", "kafka"],
)

# ================================================================
# Constants
# ================================================================
PARQUET_PATH = os.getenv("PARQUET_PATH", "/opt/airflow/database/taxi_trip_engineering_2.parquet")
TEMP_DIR = "/tmp/airflow_taxi_pipeline"
os.makedirs(TEMP_DIR, exist_ok=True)

ROW_LIMIT = int(os.getenv("INGESTION_ROW_LIMIT", 15000))

# Parquet Source -> PostgreSQL table mapping
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
    "datetime": "created_at"
}

# Internal Docker PostgreSQL connection
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
            logger.info(f"⚠️ Row limit applied: ingesting {len(df)} of {total_available} records")

        extracted_path = os.path.join(
            TEMP_DIR,
            f"extracted_{datetime.now().strftime('%Y%m%d_%H%M%S')}.parquet",
        )
        df.to_parquet(extracted_path, index=False)

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

        # Standardize column names
        df.columns = (
            df.columns.str.lower()
            .str.strip()
            .str.replace(" ", "_")
        )
        logger.info(f"📊 Normalized column names: {df.columns.tolist()}")

        # Rename to match SQL schema
        df = df.rename(columns={
            k: v for k, v in COLUMN_RENAME_MAP.items() if k in df.columns
        })

        # Handle ride_id
        if "ride_id" not in df.columns:
            for alt in ["id", "trip_id"]:
                if alt in df.columns:
                    df["ride_id"] = df[alt]
                    break
            else:
                raise ValueError("No ride_id column found")

        # Handle rider_id
        if "rider_id" not in df.columns:
            for alt in ["user_id", "passenger_id"]:
                if alt in df.columns:
                    df["rider_id"] = df[alt]
                    break
            else:
                raise ValueError("No rider_id column found")

        # Map driver_status based on booking_status
        if "booking_status" in df.columns:
            df["driver_status"] = df["booking_status"].apply(
                lambda s: "Online" if str(s).strip() == "Completed" else "Offline"
            )
            online_count = (df["driver_status"] == "Online").sum()
            offline_count = (df["driver_status"] == "Offline").sum()
            logger.info(f"✅ Mapped driver_status: Online={online_count}, Offline={offline_count}")
        else:
            df["driver_status"] = "Offline"
            logger.warning("⚠️ booking_status not found, defaulting driver_status to 'Offline'")

        # Map status column
        if "booking_status" in df.columns:
            df["status"] = df["booking_status"]
        else:
            df["status"] = "Unknown"
            df["booking_status"] = "Unknown"

        # Handle vehicle_arrival_at and completed_at - SIMPLIFIED
        # These columns may not exist in source data, so create them as NULL
        if "vehicle_arrival_at" not in df.columns:
            df["vehicle_arrival_at"] = None
        if "completed_at" not in df.columns:
            df["completed_at"] = None

        # Handle fares
        if "actual_fare" in df.columns:
            df["actual_fare"] = pd.to_numeric(df["actual_fare"], errors="coerce")
        elif "price" in df.columns:
            df["actual_fare"] = pd.to_numeric(df["price"], errors="coerce")
            logger.info("✅ Created actual_fare from price")

        if "estimated_fare" in df.columns:
            df["estimated_fare"] = pd.to_numeric(df["estimated_fare"], errors="coerce")
        else:
            estimated_fare_candidates = ["estimated_price", "fare_estimate", "predicted_fare"]
            resolved = False
            for candidate in estimated_fare_candidates:
                if candidate in df.columns:
                    df["estimated_fare"] = pd.to_numeric(df[candidate], errors="coerce")
                    resolved = True
                    break
            if not resolved:
                df["estimated_fare"] = None
                logger.warning("⚠️ estimated_fare set to NULL")

        # Coordinate columns
        coord_map = {
            "pickup_lon": "pickup_lng",
            "drop_lat": "dropoff_lat",
            "drop_lon": "dropoff_lng",
        }
        for src, dst in coord_map.items():
            if src in df.columns and dst not in df.columns:
                df[dst] = df[src]

        # Validate required columns
        required_columns = ["ride_id", "rider_id"]
        missing = [c for c in required_columns if c not in df.columns]
        if missing:
            raise ValueError(f"Required columns missing: {missing}")

        # Data cleaning
        before = len(df)
        df = df.drop_duplicates(subset=["ride_id"], keep="first")
        df = df.dropna(subset=["ride_id", "rider_id"])
        logger.info(f"✅ Cleaned data: dropped {before - len(df)} records")

        # Log null summary
        key_cols = ["ride_id", "rider_id", "booking_status", "driver_status",
                    "status", "actual_fare", "distance_km", "day_of_week", 
                    "demand_pressure", "hour", "vehicle_arrival_at", "completed_at"]
        null_summary = {c: int(df[c].isna().sum()) for c in key_cols if c in df.columns}
        logger.info(f"Null summary:\n{null_summary}")

        # Save transformed data
        transformed_path = os.path.join(TEMP_DIR, f"transformed_{datetime.now().strftime('%Y%m%d_%H%M%S')}.parquet")
        df.to_parquet(transformed_path, index=False)

        context["task_instance"].xcom_push(key="transformed_path", value=transformed_path)
        logger.info(f"✅ Transformed data saved to {transformed_path} with {len(df)} records")
        return {"rows_transformed": len(df), "file_path": transformed_path}

    except Exception as e:
        logger.exception("❌ Failed transforming data")
        raise e

# ================================================================
# Task 3: Load Into PostgreSQL
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
        logger.info(f"✅ Loading {len(df)} rows into analytics.trip")

        # Columns matching the analytics.trip schema
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
            "vehicle_arrival_at",
            "completed_at",
            "day_of_week",
            "demand_pressure",
            "hour",
            # NEW COLUMNS
            "vtat_minutes",
            "ctat_minutes",
            "pickup_encoded",
            "drop_encoded",
            "route_cluster"
        ]

        # Keep only columns that exist
        insert_cols = [c for c in trip_cols if c in df.columns]
        df_insert = df[insert_cols].copy()
        logger.info(f"📊 Columns to insert: {insert_cols}")

        # Cast float columns
        float_cols = ["pickup_lat", "pickup_lng", "dropoff_lat", "dropoff_lng",
                      "actual_fare", "estimated_fare", "distance_km",
                      "duration_minutes", "driver_rating", "demand_pressure"]
        for float_col in float_cols:
            if float_col in df_insert.columns:
                df_insert[float_col] = pd.to_numeric(df_insert[float_col], errors="coerce")

        # Cast timestamp columns
        for ts_col in ["created_at", "vehicle_arrival_at", "completed_at"]:
            if ts_col in df_insert.columns:
                df_insert[ts_col] = pd.to_datetime(df_insert[ts_col], errors="coerce")

        # Replace NaN with None
        df_insert = df_insert.where(pd.notna(df_insert), None)

        # Upsert into PostgreSQL
        conn = get_postgres_conn()
        inserted = 0
        skipped = 0

        try:
            with conn.cursor() as cur:
                for _, row in df_insert.iterrows():
                    cols = [c for c in insert_cols if row.get(c) is not None and not pd.isna(row.get(c))]
                    vals = [row[c] for c in cols]

                    if not cols:
                        skipped += 1
                        continue

                    placeholders = ", ".join(["%s"] * len(cols))
                    col_names = ", ".join(cols)
                    update_clause = ", ".join([
                        f"{c} = EXCLUDED.{c}" for c in cols if c != "ride_id"
                    ])

                    sql = f"""
                        INSERT INTO analytics.trip ({col_names})
                        VALUES ({placeholders})
                        ON CONFLICT (ride_id) 
                        DO UPDATE SET {update_clause}
                    """
                    cur.execute(sql, vals)
                    inserted += 1

            conn.commit()
            logger.info(f"✅ Loaded {inserted} records into PostgreSQL")
            if skipped > 0:
                logger.info(f"⚠️ Skipped {skipped} records with missing values")

        finally:
            conn.close()

        context["task_instance"].xcom_push(key="rows_loaded", value=inserted)

        return {
            "rows_loaded": inserted,
            "table": "analytics.trip",
        }

    except Exception as e:
        logger.exception("❌ Failed loading data into PostgreSQL")
        raise

# ================================================================
# Task 4: Cache Route Features to Redis
# ================================================================
def cache_route_features(**context):
    """Cache route features to Redis for fast API responses"""
    try:
        r = redis.Redis(host='redis', port=6379, decode_responses=True)
        conn = get_postgres_conn()

        rows = []
        with conn.cursor() as cur:
            cur.execute("""
                SELECT pickup_location, dropoff_location,
                       AVG(duration_minutes) AS avg_duration,
                       AVG(actual_fare) AS avg_fare,
                       COUNT(*) AS trip_count
                FROM analytics.trip
                WHERE status = 'Completed'
                  AND pickup_location IS NOT NULL
                  AND dropoff_location IS NOT NULL
                GROUP BY pickup_location, dropoff_location
            """)
            rows = cur.fetchall()

        cached_count = 0
        for row in rows:
            if row[0] and row[1]:  # Ensure both locations exist
                key = f"route_features:{row[0]}:{row[1]}"
                value = json.dumps({
                    "avg_duration": float(row[2]) if row[2] else None,
                    "avg_fare": float(row[3]) if row[3] else None,
                    "trip_count": row[4]
                })
                r.setex(key, 86400, value)  # 24 hour TTL
                cached_count += 1

        conn.close()
        logger.info(f"✅ Cached {cached_count} route features to Redis")

        # Also cache popular routes for quick access
        popular_routes = [
            {
                "pickup": row[0],
                "dropoff": row[1],
                "trip_count": row[4]
            }
            for row in rows[:20] if row[0] and row[1]
        ]
        r.setex("popular_routes", 3600, json.dumps(popular_routes))  # 1 hour TTL

        return {"cached_count": cached_count}

    except Exception as e:
        logger.exception("❌ Failed caching route features to Redis")
        raise

# ================================================================
# Task 5: Publish Kafka Event
# ================================================================
def publish_kafka_event(**context):
    """Publish ingestion completion event to Kafka"""
    try:
        try:
            from confluent_kafka import Producer
        except ImportError:
            logger.warning("⚠️ confluent_kafka not installed")
            return {"event_published": False, "reason": "confluent_kafka missing"}

        load_result = context["task_instance"].xcom_pull(task_ids="load_to_postgres")
        cache_result = context["task_instance"].xcom_pull(task_ids="cache_route_features")

        bootstrap_servers = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "kafka:9092")

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
                "routes_cached": cache_result.get("cached_count", 0) if cache_result else 0,
                "row_limit": ROW_LIMIT,
                "table": "analytics.trip",
            },
        }

        producer.produce(
            topic="frontend-events",
            value=json.dumps(event).encode("utf-8"),
            callback=lambda err, msg: (
                logger.error(f"❌ Kafka delivery failed: {err}") if err
                else logger.info(f"✅ Kafka event delivered to {msg.topic()}")
            ),
        )
        producer.flush(timeout=10)
        return {"event_published": True}

    except Exception as e:
        logger.exception("❌ Failed publishing Kafka event")
        raise

# ================================================================
# Task 6: Data Quality Checks
# ================================================================
def data_quality_checks(**context):
    """Run data quality validation against PostgreSQL"""
    try:
        conn = get_postgres_conn()
        results = {}

        try:
            with conn.cursor() as cur:
                # Total rows
                cur.execute("SELECT COUNT(*) FROM analytics.trip;")
                results["total_rows"] = cur.fetchone()[0]
                logger.info(f"📊 Total rows: {results['total_rows']}")

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
                results["null_checks"] = {
                    "ride_id": null_check[0],
                    "rider_id": null_check[1],
                    "estimated_fare": null_check[2],
                    "booking_status": null_check[3]
                }
                logger.info(f"✅ Null checks: {results['null_checks']}")

                # Completed rides with missing driver_status
                cur.execute("""
                    SELECT COUNT(*) 
                    FROM analytics.trip
                    WHERE booking_status = 'Completed' 
                    AND driver_status IS NULL;
                """)
                results["completed_missing_driver"] = cur.fetchone()[0]
                if results["completed_missing_driver"] > 0:
                    logger.warning(f"⚠️ {results['completed_missing_driver']} completed rides missing driver_status")

                # Invalid fares
                cur.execute("""
                    SELECT COUNT(*) 
                    FROM analytics.trip
                    WHERE actual_fare < 0 OR actual_fare IS NULL;
                """)
                results["invalid_fares"] = cur.fetchone()[0]

                # Duplicates
                cur.execute("""
                    SELECT COUNT(*) - COUNT(DISTINCT ride_id) FROM analytics.trip;
                """)
                results["duplicates"] = cur.fetchone()[0]

                # Vehicle_arrival_at null check
                cur.execute("""
                    SELECT COUNT(*) 
                    FROM analytics.trip
                    WHERE vehicle_arrival_at IS NULL AND status = 'Completed';
                """)
                results["null_vehicle_arrival"] = cur.fetchone()[0]
                logger.info(f"📊 Completed rides with NULL vehicle_arrival_at: {results['null_vehicle_arrival']}")

                # Status distribution
                cur.execute("""
                    SELECT booking_status, COUNT(*) 
                    FROM analytics.trip
                    GROUP BY booking_status
                    ORDER BY COUNT(*) DESC;
                """)
                results["status_distribution"] = cur.fetchall()
                logger.info(f"📊 Status distribution: {results['status_distribution']}")

        finally:
            conn.close()

        # Determine if quality checks pass
        results["data_quality_passed"] = (
            results["invalid_fares"] == 0
            and results["duplicates"] == 0
            and results["completed_missing_driver"] == 0
        )

        logger.info(
            f"{'✅' if results['data_quality_passed'] else '❌'} "
            f"Data quality: {'PASSED' if results['data_quality_passed'] else 'FAILED'}"
        )

        return results

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

task_cache_redis = PythonOperator(
    task_id="cache_route_features",
    python_callable=cache_route_features,
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

task_extract >> task_transform >> task_load_postgres >> task_cache_redis >> [task_kafka_event, task_quality_check]