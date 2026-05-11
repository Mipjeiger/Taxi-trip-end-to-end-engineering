from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.utils.dates import days_ago
from datetime import datetime, timedelta
import pandas as pd
import logging
import json
import os
from databricks.sql import connect
from pathlib import Path
from dotenv import load_dotenv
from plugins.supabase_hook import SupabaseHook

# env. Configuration
BASE_DIR = Path(__file__).resolve().parent.parent.parent.parent
ENV_PATH = BASE_DIR / '.env'
load_dotenv(dotenv_path=ENV_PATH)

# DATABRICKS CONFIGURATION
DATABRICKS_HOST=os.getenv("DATABRICKS_HOST")
DATABRICKS_HTTP_PATH=os.getenv("DATABRICKS_HTTP_PATH")
DATABRICKS_TOKEN=os.getenv("DATABRICKS_TOKEN")

default_args = {
    "owner" : 'taxi-trip-ML',
    'retries': 3,
    'retry_delay': timedelta(minutes=5),
    'start_date': days_ago(1)
}

# DAG definition
dag = DAG(
    'rides_data_ingestion',
    default_args=default_args,
    description='Ingest 5000 rides rows data',
    schedule='0 2 * * *', # Daily at 2 AM
    tags=['data_ingestion', 'supabase'],
    catchup=False
)

# Task 1: Fetch 5k rows from supabase
def fetch_rides_5k_rows(**context):
    """Fetch exactly 5000 rows from supabase
    Order by: created_at DESC to get the most recent rides
    """
    try:
        hook = SupabaseHook()

        # Fetch datas needed
        query = """
                    SELECT * FROM rides
                    ORDER BY created_at DESC
                    LIMIT 5000
                """
        
        df = hook.execute_query_to_dataframe(query)
        logging.info(f"✅ Successfully fetched {len(df)} rows from Supabase")

        # Save to temporary file for next task
        temp_file = "/tmp/rides_5k.parquet"
        df.to_parquet(temp_file)

        # Push to Xcom
        context['task_instance'].xcom_push(
            key='rides_data_file',
            value=temp_file
        )

        return {
            'rows_fetched': len(df),
            'file_path': temp_file,
            'columns': list(df.columns)
        }
    
    except Exception as e:
        logging.error(f"❌ Error fetching data from Supabase: {e}")
        raise

# Task 2: Validate 5k rows data
def validate_rides_data(**context):
    """
    Validate the fetched 5k rows data
    - Check NULL values
    - Check duplicates
    - Data type validation
    - Status field validation
    """
    temp_file = context['task_instance'].xcom_pull(
        task_ids='fetch_5k_task',
        key='rides_data_file'
    )
    df = pd.read_parquet(temp_file)

    # Validation checks
    validation = {
        'total_rows': len(df),
        'null_values': df.isnull().sum().to_dict(),
        'duplicate_rows': len(df[df.duplicated(subset=['id'])]),
        'price_null': df['price'].isnull().sum(),
        'valid_status': df['status'].isin([
            'Pending', 'Completed', 'Cancelled by Driver',
            'No Driver Found', 'Cancelled by Customer', 'Incomplete'
        ]).sum(),
        'date_range': {
            'earliest': str(df['created_at'].min()),
            'latest': str(df['created_at'].max())
        }
    }
    logging.info(f"📊 Validation results:\n{json.dumps(validation, indent=2)}")

    context['task_instance'].xcom_push(
        key='validation_results',
        value=validation
    )
    return validation

# Task 3: Transform data
def transform_rides_data(**context):
    """
    Transform 5k rows:
    - Add ingestion timestamp
    - Calculate metrics
    - Normalize fields
    """
    temp_file = context['task_instance'].xcom_pull(
        task_ids='fetch_5k_task',
        key='rides_data_file'
    )
    df = pd.read_parquet(temp_file)

    # Add transformatoion columns
    df['ingestion_date'] = datetime.now()
    df['data_quality_score'] = (1 - df.isnull().sum(axis=1) / len(df.columns)) * 100
    df['price_per_km'] = df.apply(
        lambda row: row['price'] / row['ride_distance'] if row['ride_distance'] > 0 else None, axis=1
    )

    # Normalize vehicle types to title case
    df['vehicle_type'] = df['vehicle_type'].str.title()

    # Save transformed data
    transformed_file = "/tmp/rides_5k_transformed.parquet"
    df.to_parquet(transformed_file)
    logging.info(f"✅ Successfully transformed data and saved to {transformed_file}")

    context['task_instance'].xcom_push(
        key='transformed_data_file',
        value=transformed_file
    )

    return {
        'rows_transformed': len(df),
        'avg_price_per_km': float(df['price_per_km'].mean()),
        'avg_data_quality_score': float(df['data_quality_score'].mean())
    }

# Task 4: Load to Databricks (as warehouse data storage)
def load_to_databricks(**context):
    """
    Load transformed 5k rows to Databricks delta table.
    Mode: APPEND (adds to existing data)"""
    # Pull transformed data file path from Xcom
    transformed_file = context['task_instance'].xcom_pull(
        task_ids='transform_data_task',
        key='transformed_file'
    )
    df = pd.read_parquet(transformed_file)

    # Connect to Databricks
    try:
        connection = connect(
            server_hostname=DATABRICKS_HOST,
            http_path=DATABRICKS_HTTP_PATH,
            access_token=DATABRICKS_TOKEN
        )

        # Prepare table name with timestamp
        from datetime import datetime
        load_timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        table_name = f"taxi_rides_ingested"

        # Create temporary view and merge
        cursor = connection.cursor()

        # Insert data into Databricks table
        for idx, row in df.iterrows():
            values = ', '.join([f"'{str(v)}'" if pd.notna(v) else 'NULL' for v in row])
            insert_query = f"""
                INSERT INTO {table_name}
                ({', '.join(df.columns)})
                VALUES ({values})
            """
            cursor.execute(insert_query)

        # Commit and close connection
        connection.commit()
        cursor.close()
        connection.close()
        logging.info(f"✅ Successfully loaded {len(df)} rows to Databricks table {table_name}")
        
        return {
            'rows_loaded': len(df),
            'table': table_name,
            'timestamp': load_timestamp
        }
    
    except Exception as e:
        logging.error(f"❌ Error loading data to Databricks: {e}")
        raise

# Task 5: Generate summary report
def generate_summary_report(**context):
    """
    Generate final report of ingestion data"""
    validation = context['task_instance'].xcom_pull(
        task_ids='validate_data_task',
        key='validation_results'
    )
    
    report = {
        'timestamp': datetime.now().isoformat(),
        'rows_ingested': 5000,
        'status': 'Success' if validation['total_rows'] == 5000 else 'Failed',
        'next_run': (datetime.now() + timedelta(days=1)).isoformat()
    }
    logging.info(f"📋 Ingestion Summary Report:\n{json.dumps(report, indent=2)}")

    return report

# =========== Define Tasks ===========
fetch_task = PythonOperator(
    task_id='fetch_5k_task',
    python_callable=fetch_rides_5k_rows,
    dag=dag
)

validate_task = PythonOperator(
    task_id='validate_task',
    python_callable=validate_rides_data,
    dag=dag
)

transform_task = PythonOperator(
    task_id='transform_task',
    python_callable=transform_rides_data,
    dag=dag
)

load_task = PythonOperator(
    task_id='load_task',
    python_callable=load_to_databricks,
    dag=dag
)

report_task = PythonOperator(
    task_id='report_task',
    python_callable=generate_summary_report,
    dag=dag
)

# Task dependencies
fetch_task >> validate_task >> transform_task >> load_task >> report_task