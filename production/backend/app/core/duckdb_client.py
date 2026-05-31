import logging
import os
import duckdb
from pathlib import Path
from dotenv import load_dotenv
from typing import Optional, Dict, List, Any

logger = logging.getLogger(__name__)

# Load environment variables
BASE_DIR = Path(__file__).resolve().parent.parent.parent
ENV_PATH = BASE_DIR / '.env'
logger.info(f"✅ Loaded environtment variables from: {ENV_PATH}")

if not ENV_PATH.exists():
    ENV_PATH = BASE_DIR.parent / '.env'
    logging.debug(f"⚠️ .env file not found at {ENV_PATH}, trying fallback location: {ENV_PATH}")

# Load .env variables   
load_dotenv(dotenv_path=ENV_PATH)

class DuckDBClient:
    """DuckDB client for data warehouse and analytics"""

    def __init__(self):
        self.db_path = os.getenv("DUCKDB_PATH", "/data/taxi_trip.duckdb")
        self.sql_init_path = Path(__file__).resolve().parent.parent.parent / "sql" / "init_duckdb.sql"
        self.conn: Optional[duckdb.DuckDBPyConnection] = None
        self.connected = False
        self._initialize()

    def _initialize(self):
        """Initialize DuckDB connection and create tables from SQL file"""
        try:
            # Ensure database directory exists
            Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)

            # Connect to DuckDB
            self.conn = duckdb.connect(self.db_path)
            self.connected = True
            logger.info(f"✅ Connected to DuckDB at {self.db_path}")

            # Create tables from SQL file
            self._create_tables_from_sql()
        except Exception as e:
            logger.error(f"❌ Failed to initialize DuckDB client: {e}")
            self.connected = False
            raise

    def _create_tables_from_sql(self):
        """Load and execute SQL statements from a file to create tables"""
        try:
            if not self.sql_init_path.exists():
                logger.error(f"❌ SQL initialization file not found at {self.sql_init_path}")
                raise FileNotFoundError(f"SQL initialization file not found at {self.sql_init_path}")
            
            # Read SQL file
            with open(self.sql_init_path, "r") as f:
                sql_script = f.read()

            # Execute SQL script
            self.conn.execute(sql_script)
            logger.info(f"✅ Successfully executed SQL initialization script from {self.sql_init_path}")

        except Exception as e:
            logger.error(f"❌ Failed to create tables from SQL file: {e}")
            raise

    def insert_event(self, event_type: str, user_id: str, topic: str,
                     event_data: Dict, event_timestamp: float):
        """Insert an event into the events table"""
        try:
            self.conn.execute("""
                INSERT INTO taxi_trip_data_events
                              (event_type, user_id, topic, event_data, event_timestamp)
                              VALUES (?, ?, ?, ?, ?)
                              """, [event_type, user_id, topic, str(event_data), event_timestamp])
            return True
        except Exception as e:
            logger.error(f"❌ Failed to insert event into DuckDB: {e}")
            return False
        
    def insert_batch_events(self, events: List[Dict]):
        """Insert batch of events"""
        try:
            for event in events:
                self.insert_event(
                    event_type=event.get("event_type"),
                    user_id=event.get("user_id"),
                    topic=event.get("topic"),
                    event_data=event.get("event_data"),
                    event_timestamp=event.get("event_timestamp")
                )
            logger.info(f"✅ Inserted batch of {len(events)} events into DuckDB")
            return True
        except Exception as e:
            logger.error(f"❌ Failed to insert batch events into DuckDB: {e}")
            return False
        
    def insert_llm_interaction(self, user_id: str, session_id: str, prompt: str, response: str,
                               response_time_ms: int, tokens_used: int, cost: float,
                               prompt_embedding: List[float] = None, response_embedding: List[float] = None):
        """Insert an LLM interaction with embeddings for semantic search"""
        try:
            self.conn.execute("""
                INSERT INTO llm_interactions
                (user_id, session_id, prompt, response, response_time_ms, tokens_used, cost,
                prompt_embedding, response_embedding)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, [user_id, session_id, prompt, response, response_time_ms, tokens_used, cost,
                      prompt_embedding, response_embedding])
            return True
        except Exception as e:
            logger.error(f"❌ Failed to insert LLM interaction into DuckDB: {e}")
            return False
        
    def query(self, sql: str) -> List[Dict]:
        """Execute SQL query and return results as list of dicts"""
        try:
            result = {
                "total_events": self.conn.execute("SELECT COUNT(*) FROM taxi_trip_data_events").fetchone()[0],
                "total_rides": self.conn.execute("SELECT COUNT(*) FROM rides").fetchone()[0],
                "total_drivers": self.conn.execute("SELECT COUNT(*) FROM drivers").fetchone()[0],
                "total_llm_interactions": self.conn.execute("SELECT COUNT(*) FROM llm_interactions").fetchone()[0],
                "avg_fare": self.conn.execute("SELECT AVG(actual_fare) FROM rides WHERE actual_fare IS NOT NULL").fetchone()[0],
                "avg_rating": self.conn.execute("SELECT AVG(rating) FROM drivers WHERE rating IS NOT NULL").fetchone()[0]
                }
            return result
        except Exception as e:
            logger.error(f"❌ Failed to execute query on DuckDB: {e}")
            return {}
        
    def close(self):
        """Close DuckDB connection"""
        try:
            if self.conn:
                self.conn.close()
                logger.info("✅ DuckDB connection closed.")
        except Exception as e:
            logger.error(f"❌ Failed to close DuckDB connection: {e}")

# Singleton instance of DuckDBClient for application-wide use
duckdb_client = DuckDBClient()