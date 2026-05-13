from supabase import create_client, Client
import os
from dotenv import load_dotenv
from pathlib import Path
import psycopg2
import pandas as pd
import logging
from datetime import datetime

# get logger
logger = logging.getLogger(__name__)

# Load env configuration
BASE_DIR = Path(__file__).resolve().parent.parent.parent
ENV_PATH = BASE_DIR / '.env'
load_dotenv(dotenv_path=ENV_PATH)

# Data parquet configuration
PARQUET_DATA_PATH = "taxi_trip_engineering.parquet"

# Supabase Configuration
SUPABASE_HOST=os.getenv("SUPABASE_HOST")
SUPABASE_PORT=os.getenv("SUPABASE_PORT")
SUPABASE_USER=os.getenv("SUPABASE_USER")
SUPABASE_PASSWORD=os.getenv("SUPABASE_PASSWORD")
SUPABASE_DB=os.getenv("SUPABASE_DB")
SUPABASE_URL=os.getenv("SUPABASE_URL")
SUPABASE_KEY=os.getenv("SUPABASE_KEY")
SUPABASE_API_KEY=os.getenv("SUPABASE_API_KEY")

# Integrate connection to psycopg2 for direct SQL operations through supabase connection parameters
def db_connection():
    """Establish connection to Supabase PostgreSQL"""
    conn = psycopg2.connect(
        host=SUPABASE_HOST,
        port=SUPABASE_PORT,
        user=SUPABASE_USER,
        password=SUPABASE_PASSWORD,
        dbname=SUPABASE_DB
    )
    cur = conn.cursor()
    cur.execute("SELECT * FROM rides;")
    rows = cur.fetchall()
    print(f"✅ Successfully connected to Supabase and fetched {len(rows)} rows from 'rides' table.")
    
    # Loop through rows and print
    for row in rows:
        print(row)
        
    # Close connection    cur.close()
    conn.close()

# Populate parquet data to supabase postgreSQL
def transform_and_load_data():
    """Transform parquet data and load to Supabase PostgreSQL"""
    
    df = pd.read_parquet(PARQUET_DATA_PATH)
    logger.info(f"✅ Successfully read {len(df)} rows from parquet file")
    
    # Select only relevant columns for loading to database
    required_columns = {
        'id': 'user_id',
        'user_id': 'Booking ID',
        'pickup_location': 'Pickup Location',
        'drop_location': 'Drop Location',
        'vehicle_type': 'Vehicle Type',
        'price': 'Booking Value',
        'estimated_pickup_time_minute': 'estimated_pickup_time_minute',
        'estimated_drop_time_minute': 'estimated_drop_time_minute',
        'status': 'Booking Status',
        'created_at': 'Datetime',
        'completed_at': 'completed_at',
        'pickup_encoded': 'Pickup Encoded',
        'drop_encoded': 'Drop Encoded',
        'hour': 'hour',
        'day_of_week': 'day_of_week',
        'route_cluster': 'route_cluster',
        'ride_distance': 'Ride Distance',
        'is_peak_hour': 'is_peak_hour',
        'is_weekend': 'is_weekend',
        'is_night': 'is_night',
        'hour_sin': 'hour_sin',
        'hour_cos': 'hour_cos',
        'day_sin': 'day_sin',
        'day_cos': 'day_cos',
        'vtat': 'Avg VTAT'
    }

    # Select only needed columns from parquet
    parquet_cols = [col for col in required_columns.values() if col in df.columns]
    df_selected = df[parquet_cols].copy()

    # Rename columns to match SQL table
    rename_map = {v: k for k, v in required_columns.items()}
    df_selected = df_selected.rename(columns=rename_map)
    logger.info(f"Selected columns: {df_selected.columns.tolist()}")
    logger.info(f"Dataframe shape: {df_selected.shape}")

    # Data type conversions if needed
    df_selected['price'] = pd.to_numeric(df_selected['price'], errors='coerce')
    df_selected['ride_distance'] = pd.to_numeric(df_selected['ride_distance'], errors='coerce')
    df_selected['estimated_pickup_time_minute'] = pd.to_numeric(df_selected['estimated_pickup_time_minute'], errors='coerce')
    df_selected['estimated_drop_time_minute'] = pd.to_numeric(df_selected['estimated_drop_time_minute'], errors='coerce')

    # Convert Datetime strings to proper timestamp
    df_selected['created_at'] = pd.to_datetime(df_selected['created_at'], errors='coerce')
    df_selected['completed_at'] = pd.to_datetime(df_selected['completed_at'], errors='coerce')
    df_selected['vtat'] = pd.to_datetime(df_selected['vtat'], errors='coerce')

    # Convert integer columns
    int_columns = ['hour', 'day_of_week', 'route_cluster', 'is_peak_hour', 'is_weekend', 'is_night',
                   'pickup_encoded', 'drop_encoded']
    for col in int_columns:
        df_selected[col] = pd.to_numeric(df_selected[col], errors='coerce').astype('Int64')

    # Float columns
    float_columns = ['hour_sin', 'hour_cos', 'day_sin', 'day_cos']
    for col in float_columns:
        df_selected[col] = pd.to_numeric(df_selected[col], errors='coerce')

    # Handle Null values if missing values are found
    df_selected = df_selected.fillna(value={
        'price': 0.0,
        'ride_distance': 0.0,
        'estimated_pickup_time_minute': 0.0,
        'estimated_drop_time_minute': 0.0,
        'status': 'Unknown',
    })

    # Check for missing values in critical columns before loading
    critical_cols = ['id', 'user_id', 'pickup_location', 'drop_location']
    if df_selected[critical_cols].isnull().any().any():
        logger.warning(f"Critical columns have missing values:\n{df_selected[critical_cols].isnull().sum()}")
        df_selected = df_selected.dropna(subset=critical_cols)

    logger.info(f"Data prepared: {len(df_selected)} rows ready to insert.")

    # Integrated: load database to supabase using psycopg2 connection
    conn = psycopg2.connect(
        host=SUPABASE_HOST,
        port=SUPABASE_PORT,
        user=SUPABASE_USER,
        password=SUPABASE_PASSWORD,
        dbname=SUPABASE_DB
    )
    cur = conn.cursor()
    logger.info("🚀 Starting data load to Supabase...")

    # Prepare insert statement with correct columns
    columns = list(df_selected.columns)
    placeholders = ', '.join(['%s'] * len(columns))
    insert_query = f"""
        INSERT INTO rides ({', '.join(columns)})
        VALUES ({placeholders})
        """
    
    # Loop through dataframe and insert data parquet into rows table
    for index, row in df.iterrows():
        try:
            cur.execute(insert_query, tuple(row))

        # Chunk every 100 rows to avoid memory issues until all rows are inserted
            if index % 100 == 0:
                conn.commit()
                logger.info(f"Inserted {index} rows...")
        except Exception as e:
            logger.error(f"Error inserting row {index}: {str(e)}")
            conn.rollback() # Rollback on error to avoid partial commits
            continue

    conn.commit()
    logger.info(f"✅ Successfully loaded {len(df)} rows to Supabase.")
    cur.close()
    conn.close()
    

# Run connection check
if __name__ == "__main__":
    db_connection() # Check connection and fetch data from Supabase
    transform_and_load_data() # Transform and load data from parquet to Supabase