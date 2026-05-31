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
    """
    DuckDB client for data warehouse and analytics.
    Uses per-operation connections so the file lock is released
    between writes — allowing DuckDB UI to connect simultaneously.
    """

    def __init__(self):
        self.db_path = os.getenv("DUCKDB_PATH", "/data/taxi_trip.duckdb")
        self.sql_init_path = Path(__file__).resolve().parent.parent.parent / "sql" / "init_duckdb.sql"
        self.connected = False
        self._initialize()

    def _get_conn(self) -> duckdb.DuckDBPyConnection:
        """Open a fresh read-write connection. Caller is responsible for closing it."""
        return duckdb.connect(self.db_path)

    def _initialize(self):
        """Run the SQL init script once at startup, then immediately
        close the connection so no permanent lock is held."""
        try:
            # Ensure database directory exists
            Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)

            # Connect to DuckDB
            with self._get_conn() as con:
                self._create_tables_from_sql(con)

            self.connected = True
            logger.info(f"✅ Connected to DuckDB at {self.db_path}")

        except Exception as e:
            logger.error(f"❌ Failed to initialize DuckDB client: {e}")
            self.connected = False
            raise

    def _create_tables_from_sql(self, con: duckdb.DuckDBPyConnection):
        """Load and execute SQL statements from a file to create tables"""
        try:
            if not self.sql_init_path.exists():
                logger.error(f"❌ SQL initialization file not found at {self.sql_init_path}")
                raise FileNotFoundError(f"SQL initialization file not found at {self.sql_init_path}")
            
            # Read SQL file
            with open(self.sql_init_path, "r") as f:
                sql_script = f.read()

            # Execute SQL script
            con.execute(sql_script)
            logger.info(f"✅ Successfully executed SQL initialization script from {self.sql_init_path}")

        except Exception as e:
            logger.error(f"❌ Failed to create tables from SQL file: {e}")
            raise

    def insert_event(self, event_type: str, user_id: str, topic: str,
                     event_data: Dict, event_timestamp: float):
        """Insert an event into the events table"""
        try:
            with self._get_conn() as con:
                con.execute("""
                    INSERT INTO taxi_trip_data_events
                                  (event_type, user_id, topic, event_data, event_timestamp)
                                  VALUES (?, ?, ?, ?, ?)
                                  """, [event_type, user_id, topic, str(event_data), event_timestamp])
            return True
        except Exception as e:
            logger.error(f"❌ Failed to insert event into DuckDB: {e}")
            return False
        
    def insert_batch_events(self, events: List[Dict]) -> bool:
        """Insert a batch of Kafka events in a single connection/transaction.
        Much faster than one connection per event."""
        try:
            with self._get_conn() as con:
                con.executemany(
                    """
                    INSERT INTO taxi_trip_data_events
                        (event_type, user_id, topic, event_data, event_timestamp)
                    VALUES (?, ?, ?, ?, ?)
                    """,
                    [
                        [
                            event.get("event_type"),
                            event.get("user_id"),
                            event.get("topic"),
                            str(event.get("event_data", {})),
                            event.get("event_timestamp"),
                        ]
                        for event in events
                    ],
                )
            logger.info(f"✅ Inserted batch of {len(events)} events into DuckDB.")
            return True
        except Exception as e:
            logger.error(f"❌ Failed to insert batch events into DuckDB: {e}")
            return False
        
    def insert_llm_interaction(self, user_id: str, session_id: str, prompt: str, response: str,
                               response_time_ms: int, tokens_used: int, cost: float,
                               prompt_embedding: List[float] = None, response_embedding: List[float] = None):
        """Insert an LLM interaction with embeddings for semantic search"""
        try:
            with self._get_conn() as con:
                con.execute("""
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
    
    # --- Read Operations ---
    def query(self, sql: str) -> List[Dict]:
        """Return summary counts and averages across all tables.
        The sql parameter is kept for API compatibility but not used —
        summary stats are always returned."""
        try:
            with self._get_conn() as con:
                result = {
                    "total_events": con.execute("SELECT COUNT(*) FROM taxi_trip_data_events").fetchone()[0],
                    "total_rides": con.execute("SELECT COUNT(*) FROM rides").fetchone()[0],
                    "total_drivers": con.execute("SELECT COUNT(*) FROM drivers").fetchone()[0],
                    "total_llm_interactions": con.execute("SELECT COUNT(*) FROM llm_interactions").fetchone()[0],
                    "avg_fare": con.execute("SELECT AVG(actual_fare) FROM rides WHERE actual_fare IS NOT NULL").fetchone()[0],
                    "avg_rating": con.execute("SELECT AVG(rating) FROM drivers WHERE rating IS NOT NULL").fetchone()[0]
                    }
            return result
        except Exception as e:
            logger.error(f"❌ Failed to execute query on DuckDB: {e}")
            return {}
        
    def raw_query(self, sql: str) -> List[Dict]:
        """Run any arbitrary SQL and return results as a list of dicts.
        Used by analytics routes."""
        try:
            with self._get_conn() as con:
                result = con.execute(sql)
                columns = [desc[0] for desc in result.description]
                rows = result.fetchall()
                return [dict(zip(columns, row)) for row in rows]
        except Exception as e:
            logger.error(f"❌ Failed to execute raw query on DuckDB: {e}")
            return []
        
    def close(self):
        """No persistent connection to close.
        Called by shutdown handler for compatibility."""
        logger.info("✅ DuckDB connection closed.")

# Singleton instance of DuckDBClient for application-wide use
duckdb_client = DuckDBClient()