from airflow.hooks.base import BaseHook
import psycopg2
import pandas as pd
import logging
from contextlib import closing

class SupabaseHook(BaseHook):
    """
    Custom Airflow hook for Supabase PostgreSQL connection.
    Implements chunked data fetching from rides tables.
    """

    def __init__(self, supabase_conn_id = 'supabase_default'):
        self.conn_id = supabase_conn_id
        self.connection = self.get_connection(supabase_conn_id)

    def get_db_connection(self):
        """Create database connection to Supabase PostgreSQL."""
        return psycopg2.connect(
            host=self.connection.host,
            port=self.connection.port,
            user=self.connection.login,
            password=self.connection.password,
            database=self.connection.schema or 'postgres',
            sslmode='require'  # Ensure SSL connection for Supabase
        )
    
    def execute_query_to_dataframe(self, query):
        """Execute query and return Pandas DataFrame."""
        try:
            with closing(self.get_db_connection()) as conn:
                df = pd.read_sql_query(query, conn)
                logging.info(f"✅ Successfully executed query: {query}")
                return df
        except Exception as e:
            logging.error(f"❌ Error executing query: {query} - {e}")
            raise
        
    def get_row_count(self, table_name):
        """Get total row count from table"""
        query = f"SELECT COUNT(*) FROM {table_name}"
        df = self.execute_query_to_dataframe(query)
        return df['count'].iloc[0]
    
    def fetch_rows_data(self, table_name='rides', order_by='created_at'):
        """Fetch EXACTLY 5000 rows from rides table.
        Returns: Pandas DataFrame with 5K rows"""
        query = f"""SELECT * FROM {table_name}
                    ORDER BY {order_by} DESC
                    LIMIT 5000"""
        
        logging.info(f"🔍 Fetching 5000 rows from {table_name} ordered by {order_by}")
        df = self.execute_query_to_dataframe(query)
        logging.info(f"✅ Fetched {len(df)} rows from {table_name}")
        
        return df