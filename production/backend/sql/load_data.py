import os
from dotenv import load_dotenv
from pathlib import Path
import psycopg2
import pandas as pd
import logging
import time
from datetime import datetime

# Configure logging to show all levels
logging.basicConfig(
    level=logging.DEBUG,  # Changed from default
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),  # Print to console
        logging.FileHandler('load_data.log')  # Also save to file
    ]
)

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

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

# Get connection DB to postgresql
def get_connection():
    """Establish connection to Supabase postgresql"""
    max_retries = 3
    for attempt in range(max_retries):
        try:
            conn = psycopg2.connect(
                host=SUPABASE_HOST,
                port=SUPABASE_PORT,
                user=SUPABASE_USER,
                password=SUPABASE_PASSWORD,
                dbname=SUPABASE_DB
            )
            logger.info("✅ Successfully connected to Supabase PostgreSQL")
            return conn
        except Exception as e:
            logger.error(f"❌ Connection attempt {attempt + 1} failed: {str(e)}")
            if attempt < max_retries - 1:
                time.sleep(5)  # Wait before retrying
            else:
                raise

# Get Supabase client for external imports
def get_supabase_client():
    """
    Get a Supabase PostgreSQL connection for external modules.
    Returns a psycopg2 connection object that can be used for queries.
    
    Usage:
        conn = get_supabase_client()
        cur = conn.cursor()
        cur.execute("SELECT * FROM rides WHERE id = %s", (ride_id,))
        result = cur.fetchone()
        cur.close()
    """
    return get_connection()


# Integrate connection to psycopg2 for direct SQL operations through supabase connection parameters
def db_connection():
    """Establish connection to Supabase PostgreSQL"""
    conn =get_connection()
    cur = conn.cursor()
    cur.execute("SELECT * FROM rides;")
    rows = cur.fetchall()
    print(f"✅ Successfully connected to Supabase and fetched {len(rows)} rows from 'rides' table.")
    
    # Loop through rows and print
    for row in rows:
        print(row)
        
    return conn

# Retrieve data from rides table in chunks with progress tracking
def retrieve_data_by_chunks(chunk_size=100, max_rows=15000):
    """Retrieve data from rides table in chunks with progress tracking"""
    
    print("\n📊 DEBUG: Starting retrieve_data_by_chunks function...")  # Use print for immediate output
    
    conn = None
    cur = None
    try:
        conn = get_connection()
        cur = conn.cursor()
        
        print("📊 DEBUG: Connection established for retrieval")
        logger.info("📊 Starting data retrieval with chunks...")
        
        # Get total count
        print("📊 DEBUG: Executing COUNT query...")
        cur.execute("SELECT COUNT(*) FROM rides;")
        total_rows_in_db = cur.fetchone()[0]
        print(f"📊 DEBUG: Total rows = {total_rows_in_db}")
        logger.info(f"Total rows in database: {total_rows_in_db}")

        # Use the samller of max_rows or total_rows_in_db
        total_rows_to_retrieve = min(max_rows, total_rows_in_db)
        print(f"📊 DEBUG: Will retrieve up to {total_rows_to_retrieve}")
        logger.info(f"Will retrieve up to {total_rows_to_retrieve} rows")
        logger.info(f"Retrieving limited to: {total_rows_to_retrieve} rows")

        
        if total_rows_to_retrieve == 0:
            print("⚠️  DEBUG: No rows in database")
            logger.warning("No data to retrieve")
            return [], 0
        
        # Calculate chunks
        total_chunks = (total_rows_to_retrieve // chunk_size) + (1 if total_rows_to_retrieve % chunk_size > 0 else 0)
        print(f"📊 DEBUG: Will retrieve {total_chunks} chunks")
        logger.info(f"Will retrieve in {total_chunks} chunks of {chunk_size} rows")
        
        # Retrieve in chunks
        offset = 0
        all_data = []
        retrieved_count = 0
        
        for chunk_num in range(total_chunks):
            # Stop if reached max_rows
            if retrieved_count >= total_rows_to_retrieve:
                print(f"📊 DEBUG: Reached maximum rows limit ({total_rows_to_retrieve})")
                break

            try:
                # Adjust last chunk size if it exceeds max_rows
                current_chunk_size = min(chunk_size, total_rows_to_retrieve - retrieved_count)

                query = f"""
                    SELECT * FROM rides 
                    ORDER BY id 
                    LIMIT %s OFFSET %s
                """
                cur.execute(query, (current_chunk_size, offset))
                chunk_data = cur.fetchall()
                
                if not chunk_data:
                    print(f"⚠️  DEBUG: Chunk {chunk_num + 1} returned no data")
                    break
                
                all_data.extend(chunk_data)
                retrieved_count += len(chunk_data)
                
                progress_percent = (retrieved_count / total_rows_to_retrieve) * 100
                msg = f"✅ Chunk {chunk_num + 1}/{total_chunks}: {len(chunk_data)} rows | Total: {retrieved_count}/{total_rows_to_retrieve} ({progress_percent:.1f}%)"
                print(f"📊 {msg}")  # Print immediately
                logger.info(msg)
                
                offset += chunk_size
                
            except Exception as e:
                print(f"❌ ERROR in chunk {chunk_num + 1}: {str(e)}")
                logger.error(f"Error retrieving chunk {chunk_num + 1}: {str(e)}")
                continue
        
        print(f"\n✅ DEBUG: Retrieval complete - {retrieved_count} rows")
        logger.info(f"✅ Data retrieval complete: {retrieved_count} total rows")
        
        return all_data, total_rows_to_retrieve
        
    except Exception as e:
        print(f"❌ DEBUG: Fatal error in retrieve_data_by_chunks: {str(e)}")
        logger.error(f"Error during retrieval: {str(e)}")
        import traceback
        traceback.print_exc()
        return [], 0
    
    finally:
        try:
            if cur:
                cur.close()
            if conn and not conn.closed:
                conn.close()
            print("📊 DEBUG: Connection closed")
        except Exception as e:
            print(f"⚠️  DEBUG: Error closing connection: {str(e)}")

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
        'created_at': 'Datetime',
        'completed_at': 'completed_at',
        'vehicle_type': 'Vehicle Type',
        'price': 'Booking Value',
        'estimated_pickup_time_minute': 'estimated_pickup_time_minute',
        'estimated_drop_time_minute': 'estimated_drop_time_minute',
        'booking_status': 'Booking Status',
        'driver_status': 'Driver Status',
        'avg_rating': 'avg_rating',
        'pickup_encoded': 'Pickup Encoded',
        'drop_encoded': 'Drop Encoded',
        'hour': 'hour',
        'day_of_week': 'day_of_week',
        'route_cluster': 'route_cluster',
        'ride_distance': 'Ride Distance',
        'is_peak_hour': 'is_peak_hour',
        'is_weekend': 'is_weekend',
        'is_night': 'is_night',
        'pickup_lat': 'pickup_lat',
        'pickup_lon': 'pickup_lon',
        'drop_lat': 'drop_lat',
        'drop_lon': 'drop_lon',
        'hour_sin': 'hour_sin',
        'hour_cos': 'hour_cos',
        'day_sin': 'day_sin',
        'day_cos': 'day_cos'
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
    df_selected['avg_rating'] = pd.to_numeric(df_selected['avg_rating'], errors='coerce')

    # Convert Datetime strings to proper timestamp
    df_selected['created_at'] = pd.to_datetime(df_selected['created_at'], errors='coerce')
    df_selected['completed_at'] = pd.to_datetime(df_selected['completed_at'], errors='coerce')

    # Convert integer columns
    int_columns = ['hour', 'day_of_week', 'route_cluster', 'is_peak_hour', 'is_weekend', 'is_night',
                   'pickup_encoded', 'drop_encoded']
    for col in int_columns:
        df_selected[col] = pd.to_numeric(df_selected[col], errors='coerce').astype('Int64')

    # Float columns
    float_columns = ['hour_sin', 'hour_cos', 'day_sin', 'day_cos', 'avg_rating', 'pickup_lat', 'pickup_lon', 'drop_lat', 'drop_lon']
    for col in float_columns:
        df_selected[col] = pd.to_numeric(df_selected[col], errors='coerce')

    # Handle Null values if missing values are found
    df_selected = df_selected.fillna(value={
        'price': 0.0,
        'ride_distance': 0.0,
        'estimated_pickup_time_minute': 0.0,
        'estimated_drop_time_minute': 0.0,
        'status': 'Unknown',
        'avg_rating': float(df_selected['avg_rating'].mean()) if not df_selected['avg_rating'].isnull().all() else 0.0
    })

    # Truncate string columns to match database schema limits
    string_length_limits = {
        "status": 20,
        "vehicle_type": 50,
        "id": 100,
        "user_id": 100,
    }    

    for col, max_length in string_length_limits.items():
        try:
            if col in df_selected.columns:
                df_selected[col] = df_selected[col].astype(str).str[:max_length]
                
                # Log if truncation occurred
                truncated = df_selected[col].str.len().max()
                if truncated == max_length:
                    logger.warning(f"Column '{col}' values truncated to {max_length} characters.")
        # Getting debug if any error occurs during truncation
        except Exception as e:
            logger.error(f"Error inserting row {index}: {str(e)}")
            logger.error(f"Row data length: {len(row_data)}, Expected: {len(columns)}")

            # Log which columns have problematic values
            for col_name, value in zip(columns, row_data):
                if isinstance(value, str) and len(value) > 50:
                    logger.error(f"Column '{col_name}': length={len(value)}, value='{value[:100]}'")

            conn.rollback() # Rollback on error to avoid partial commits
            continue

    # Check for missing values in critical columns before loading
    critical_cols = ['id', 'user_id', 'pickup_location', 'drop_location']
    if df_selected[critical_cols].isnull().any().any():
        logger.warning(f"Critical columns have missing values:\n{df_selected[critical_cols].isnull().sum()}")
        df_selected = df_selected.dropna(subset=critical_cols)

    logger.info(f"Data prepared: {len(df_selected)} rows ready to insert.")

    # Get existing IDs from database FIRST
    conn = db_connection() # Establish connection to Supabase PostgreSQL
    cur = conn.cursor()

    logger.info("Fetching existing IDs from database to avoid duplicates...")
    cur.execute("SELECT id FROM rides;")
    existing_ids = set(row[0] for row in cur.fetchall())
    logger.info(f"Found {len(existing_ids)} existing IDs in database.")

    # Filter: only insert rows with NEW IDs
    df_to_insert = df_selected[~df_selected['id'].isin(existing_ids)].copy()
    logger.info(f"Filtered to insert {len(df_to_insert)} new rows.")

    if len(df_to_insert) == 0:
        logger.warning("No new rows to insert after filtering existing IDs. Exiting load process.")
        cur.close()
        conn.close()
        return

    # Prepare insert statement with correct columns
    columns = list(df_selected.columns)
    placeholders = ', '.join(['%s'] * len(columns))
    insert_query = f"""
        INSERT INTO rides ({', '.join(columns)})
        VALUES ({placeholders})
        """
    
    logger.info("🚀 Starting data load to Supabase...")

    # Define batch
    batch_size = 500
    sucessful_rows = 0
    failed_rows = 0
    
    # Loop through dataframe and insert data parquet into rows table
    for index, row in df_selected.iterrows():
        try:
            if conn.closed:
                logger.warning("Connection closed, reopening...")
                conn = db_connection()
                cur = conn.cursor()

            row_data = tuple(None if pd.isna(val) else val for val in row)
            cur.execute(insert_query, row_data)
            sucessful_rows += 1

            if sucessful_rows % batch_size == 0:
                conn.commit()
                logger.info(f"Inserted {sucessful_rows} rows...")

        except psycopg2.OperationalError as e:
            failed_rows += 1
            logger.error(f"Connection error at row {index}: {str(e)}")
            try:
                conn.rollback()
            except:
                pass

            try:
                conn = db_connection()
                cur = conn.cursor()
                logger.info("Reconnected successfully.")
            except Exception as reconnection_error:
                logger.error(f"Failed to reconnect: {str(reconnection_error)}")
                break

        except Exception as e:
            failed_rows += 1
            logger.error(f"Error inserting row {index}: {str(e)}")
            try:
                conn.rollback()
            except:
                pass
            continue

    # Chunk every 100 rows to avoid memory issues until all rows are inserted
        if index % 100 == 0:
            conn.commit()
            logger.info(f"Inserted {index} rows...")
    
    # Final commit connection
    try:
        conn.commit()
        logger.info(f"✅ Successfully loaded {len(df_selected)} rows to Supabase.")
    except:
        logger.error("Final commit failed")
    
    logger.info(f"✅ Load complete - Successful: {sucessful_rows}, Failed: {failed_rows}")

    try:
        cur.close()
        conn.close()
        logger.info("Connection closed successfully.")
    except:
        logger.warning("Connection already closed or failed to close.")
    

# Run connection check
if __name__ == "__main__":
    import sys
    
    print("\n" + "="*70)
    print("TAXI TRIP DATA PIPELINE - Starting")
    print("="*70)
    
    try:
        print("\n[1/3] Testing connection...")
        conn = db_connection()
        conn.close()
        print("✅ Connection OK\n")
        
        print("[2/3] Loading data...")
        transform_and_load_data()
        print("✅ Data loading OK\n")
        
        print("[3/3] Retrieving data with progress...")
        print("-" * 70)
        data, total = retrieve_data_by_chunks(chunk_size=100, max_rows=15000)
        print("-" * 70)
        
        print("\n" + "="*70)
        print("PIPELINE SUMMARY")
        print("="*70)
        print(f"Total rows in database: {total}")
        print(f"Retrieved rows: {len(data)}")
        print(f"Success rate: {(len(data)/total*100):.1f}%" if total > 0 else "No data")
        print("="*70)
        print("✅ PIPELINE COMPLETED\n")
        
    except Exception as e:
        print(f"\n❌ PIPELINE FAILED: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)