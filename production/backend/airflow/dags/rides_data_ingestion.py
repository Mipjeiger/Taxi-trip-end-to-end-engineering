import logging
import os
import json
from pathlib import Path
from dotenv import load_dotenv
from datetime import datetime, timedelta

# Airflow imports
from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.operators.bash import BashOperator
from airflow.utils.decorators import apply_defaults
from airflow.models import Variable

# Data processing imports
import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)

"""
Airflow DAG: Taxi Ride Data Ingestion Pipeline Replaces Databricks with DuckDB for data warehouse
Integrates Kafka for event streaming
"""

# ================================================================
# Load Environment Variables
# ================================================================

BASE_DIR = Path(__file__).resolve().parent.parent.parent
ENV_PATH = BASE_DIR / '.env'
if not ENV_PATH.exists():
    ENV_PATH = BASE_DIR.parent / '.env'
load_dotenv(dotenv_path=ENV_PATH)

# ================================================================
# DAG Configuration
# ================================================================

default_args = {
    'owner': 'taxi-trip-team',
    'retries': 2,
    'retry_delay': timedelta(minutes=5),
    'start_date': datetime(2026, 1, 1),
    'email_on_failure': False,
    'email_on_retry': False,
}

dag = DAG(
    dag_id='rides_data_ingestion',
    default_args=default_args,
    description='Ingest ride data from Parquet to DuckDB with Kafka events streaming',
    catchup=False,
    schedule=None, # Set to None for manual trigger or use a cron expression for scheduled runs (Optional)
    tags=['taxi-trip', 'duckdb', 'kafka']
)

# ================================================================
# Task 1: Extract Data from Parquet
# ================================================================

def extract_parquet_data(**context):
    """Load ride data from Parquet file"""
    try:
        # Use production data: taxi_trip_engineering.parquet
        parquet_path = "/backend/database/taxi_trip_engineering.parquet"

        if not os.path.exists(parquet_path):
            raise FileNotFoundError(f"Parquet file not found at {parquet_path}")
        
        df = pd.read_parquet(parquet_path)
        logger.info(f"✅ Extracted {len(df)} records from Parquet file at {parquet_path}")
        logger.info(f"📊 Columns: {list(df.columns)}")

        # Save to XCom for next task
        context['task_instance'].xcom_push(
            key='extracted_data',
            value=df.to_json(orient='records', date_format='iso')
        )

        return {
            'rows_extracted': len(df),
            'columns': list(df.columns),
            'timestamp': datetime.now().isoformat()
        }
    
    except Exception as e:
        logger.error(f"❌ Failed to extract data from Parquet: {str(e)}")
        raise

# ================================================================
# Task 2: Transform Data
# ================================================================

def transform_data(**context):
    """Transform ride data with feature engineering"""
    try:
        # Get extracted data from Xcom
        task_instance = context['task_instance']
        json_data = task_instance.xcom_pull(
            task_ids='extract_parquet',
            key='extracted_data'
        )

        df = pd.read_json(json_data, orient='records')
        logger.info(f"✅ Loaded extracted data into DataFrame with {len(df)} records")

        # Standardize column names
        df.columns = df.columns.str.lower().str.replace(' ', '_')

        # Data cleaning
        df = df.drop_duplicates(subset=['ride_id'], keep='first')
        df = df.dropna(subset=['ride_id', 'user_id'])

        # Feature engineering
        if 'distance_km' in df.columns and 'duration_minutes' in df.columns:
            df['avg_speed'] = df['distance_km'] / (df['duration_minutes'] / 60 + 1e-3) # Avoid division by zero

        if 'actual_fare' in df.columns and 'distance_km' in df.columns:
            df['fare_per_km'] = df['actual_fare'] / (df['distance_km'] + 1e-3) # Avoid division by zero

        # Add ingestion timestamp
        df['ingestion_timestamp'] = datetime.now().isoformat()

        logger.info(f"✅ Transformed data with new features. Sample:\n{df.head()}")
        logger.info(f"   Features added: avg_speed, fare_per_km, ingestion_timestamp")

        # Save transformed data to XCom for next task
        task_instance.xcom_push(
            key='transformed_data',
            value=df.to_json(orient='records', date_format='iso')
        )

        return {
            'rows_transformed': len(df),
            'timestamp': datetime.now().isoformat()
        }
    
    except Exception as e:
        logger.error(f"❌ Failed to transform data: {str(e)}")
        raise

# ================================================================
# Task 3: Load to DuckDB
# ================================================================

def load_to_duckdb(**context):
    """Load transformed data to DuckDB warehouse"""
    try:
        import duckdb

        # Get transformed data from XCom
        task_instance = context['task_instance']
        json_data = task_instance.xcom_pull(
            task_ids='transform_data',
            key='transformed_data'
        )

        # Read JSON data into DataFrame
        df = pd.read_json(json_data, orient='records')

        # Connect to DuckDB
        duckdb_path = os.getenv("DUCKDB_PATH")
        conn = duckdb.connect(duckdb_path)
        logger.info(f"✅ Connected to DuckDB at {duckdb_path}")

        # Insert data into DuckDB table
        table_name = 'rides'
        rows_inserted = 0
        rows_skipped = 0

        try:
            for _, row in df.iterrows():
                try:
                    conn.execute(f"""
                        INSERT INTO {table_name}
                        (ride_id, rider_id, driver_id, pickup_location, dropoff_location,
                         pickup_lat, pickup_lng, dropoff_lat, dropoff_lng,
                         status, ride_type, estimated_fare, actual_fare,
                         distance_km, duration_minutes, created_at, completed_at)
                         VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, [
                        row.get('ride_id'),
                        row.get('rider_id'),
                        row.get('driver_id'),
                        row.get('pickup_location'),
                        row.get('dropoff_location'),
                        row.get('pickup_lat'),
                        row.get('pickup_lng'),
                        row.get('dropoff_lat'),
                        row.get('dropoff_lng'),
                        row.get('status'),
                        row.get('ride_type'),
                        row.get('estimated_fare'),
                        row.get('actual_fare'),
                        row.get('distance_km'),
                        row.get('duration_minutes'),
                        row.get('created_at'),
                        row.get('completed_at')
                    ])
                    rows_inserted += 1
                except Exception as row_err:
                    rows_skipped += 1
                    logger.debug(f"⚠️ Skipped row due to error: {row_err}")
            
            conn.commit()
            logger.info(f"✅ Loaded data to DuckDB: {rows_inserted} rows inserted")
            logger.info(f"⚠️ {rows_skipped} rows skipped due to errors during insertion")

        except Exception as e:
            logger.error(f"❌ Failed to load data to DuckDB: {str(e)}")
            conn.rollback()
            raise

        finally:
            conn.close()
            logger.info("✅ DuckDB connection closed")

        return {
            'rows_loaded': rows_inserted,
            'rows_skipped': rows_skipped,
            'table': table_name,
            'timestamp': datetime.now().isoformat()
        }
    
    except Exception as e:
        logger.error(f"❌ Failed to load data to DuckDB: {str(e)}")
        raise

# ================================================================
# Task 4: Publish Kafka Event
# ================================================================

def publish_kafka_event(**context):
    """Publish data ingestion events to Kafka"""
    try:
        try:
            from confluent_kafka import Producer
        except ImportError:
            logger.warning("⚠️ confluent_kafka library not found. Kafka event publishing will be skipped.")
            return {'event_published': False, 'reason': 'confluent_kafka not installed'}
        
        # Get load results from XCom
        task_instance = context['task_instance']
        load_result = task_instance.xcom_pull(task_ids='load_to_duckdb')

        # Kafka configuration
        bootstrap_servers = os.getenv("KAFKA_BOOTSTRAP_SERVERS")
        config = {
            'bootstrap.servers': bootstrap_servers,
            'client.id': 'airflow-producer'
        }
        producer = Producer(config)

        # Create data ingestion event
        event = {
            'event_type': 'data_ingestion_complete',
            'user_id': 'airflow_dag',
            'topic': 'frontend-events',
            'event_data': {
                'dag_id': context['dag'].dag_id,
                'task_id': context['task'].task_id,
                'rows_loaded': load_result.get('rows_loaded'),
                'rows_skipped': load_result.get('rows_skipped'),
                'table': load_result.get('table'),
                'duckdb_path': os.getenv("DUCKDB_PATH"),
                'timestamp': load_result.get('timestamp')
            },
            'event_timestamp': datetime.now().timestamp()
        }

        # Publish event to Kafka
        producer.Produce(
            topic='frontend-events',
            value=json.dumps(event).encode('utf-8'),
            callback=delivery_report
        )

        # Flush producer to ensure delivery
        producer.flush()
        logger.info(f"✅ Published data ingestion event to Kafka topic 'frontend-events': {event}")

        return {
            'event_published': 1,
            'timestamp': datetime.now().isoformat()
        }
    
    except Exception as e:
        logger.error(f"❌ Failed to publish Kafka event: {str(e)}")
        raise

# ================================================================
# Task 5: Data Quality Check
# ================================================================

def data_quality_checks(**context):
    """Validate data quality in DuckDB"""
    try:
        import duckdb

        duckdb_path = os.getenv("DUCKDB_PATH")
        conn = duckdb.connect(duckdb_path)

        # Check 1: Total row count
        count_result = conn.execute("SELECT COUNT(*) FROM rides").fetchone()
        total_count = count_result[0] if count_result else 0
        logger.info(f"✅ Total rides rows in DuckDB: {total_count}")

        # Check 2: Missing values in columns
        missing_resulst = conn.execute("""
            SELECT
                COUNT(*) as total_rows,
                SUM(CASE WHEN ride_is IS NULL THEN 1 ELSE 0 END) as null_ride_id,
                SUM(CASE WHEN user_id IS NULL THEN 1 ELSE 0 END) as null_user_id,
                SUM(CASE WHEN driver_id IS NULL THEN 1 ELSE 0 END) as null_driver_id
            FROM rides
        """).fetchone()

        if missing_resulst:
            logger.info(f"✅ Missing values - ride_id: {missing_resulst[1]}, user_id: {missing_resulst[2]}, driver_id: {missing_resulst[3]}")

        # Check 3: Fare validation
        invalid_fares = conn.execute("""
            SELECT COUNT(*) FROM rides WHERE actual_fare < 0 OR actual_fare IS NULL
        """).fetchone()

        invalid_fare_count = invalid_fares[0] if invalid_fares else 0
        if invalid_fare_count > 0:
            logger.warning(f"⚠️ Found {invalid_fare_count} rides with invalid fares (negative or null)")
        else:
            logger.info("✅ All rides have valid fares")

        # Close connection
        conn.close()

        return {
            'total_rows': total_count,
            'invalid_fares': invalid_fare_count,
            'data_quality_passed': invalid_fare_count == 0,
            'timestamp': datetime.now().isoformat()
        }
    
    except Exception as e:
        logger.error(f"❌ Data quality checks failed: {str(e)}")
        raise

# ================================================================
# Kafka delivery report callback
# ===============================================================

def delivery_report(err, msg):
    """Callback for Kafka message delivery reports"""
    if err is not None:
        logger.error(f"❌ Kafka message delivery failed: {err}")
    else:
        logger.debug(f"✅ Kafka message delivered to {msg.topic()} [{msg.partition()}] at offset {msg.offset()}")

# ================================================================
# Task Operators
# ================================================================

task_extract = PythonOperator(
    task_id='extract_parquet',
    python_callable=extract_parquet_data,
    dag=dag
)

task_transform = PythonOperator(
    task_id='transform_data',
    python_callable=transform_data,
    dag=dag
)

task_load_duckdb = PythonOperator(
    task_id='load_to_duckdb',
    python_callable=load_to_duckdb,
    dag=dag
)

task_kafka_event = PythonOperator(
    task_id='publish_kafka_event',
    python_callable=publish_kafka_event,
    dag=dag
)

task_quality_check = PythonOperator(
    task_id='data_quality_checks',
    python_callable=data_quality_checks,
    dag=dag
)

# ================================================================
# Task Dependencies
# ================================================================
task_extract >> task_transform >> task_load_duckdb >> [task_kafka_event, task_quality_check]