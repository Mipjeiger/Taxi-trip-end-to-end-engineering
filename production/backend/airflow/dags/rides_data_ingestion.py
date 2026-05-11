from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.utils.dates import days_ago
from datetime import datetime, timedelta
import pandas as pd
import logging
import json

default_args = {
    "owner" : 'taxi-trip-ML',
    'retreies': 3,
    'retry_delay': timedelta(minutes=5),
    'start_date': days_ago(1)
}

# DAG definition
dag = DAG(
    'rides_data_ingestion',
    default_args=default_args,
    description='Ingest 5000 rides rows data',
    schedule='0 2 * * *', # Daily at 2 AM
    catchup=False
)

# Task 1: Fetch 5k rows from supabase
def fetch_rides_5k_rows(**context):
    """Fetch exactly 5000 rows from supabase
    Order by: created_at DESC to get the most recent rides
    """
    from 