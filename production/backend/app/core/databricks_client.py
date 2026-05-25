import os
import logging
from pathlib import Path
from typing import Optional, Dict, Any
from databricks.sdk import WorkspaceClient
from databricks.sdk.service.compute import ClusterDetails
from databricks.sdk.service.jobs import Job
from dotenv import load_dotenv

# env. Configuration
BASE_DIR = Path(__file__).resolve().parent.parent.parent
ENV_PATH = BASE_DIR / '.env'
load_dotenv(dotenv_path=ENV_PATH)

logger = logging.getLogger(__name__)

class DatabricksClient:
    """Databricks workspace and cluster management client."""

    def __init__(self):
        self.client: Optional[WorkspaceClient] = None
        self.connected = False
        self.initialize()

    def initialize(self):
        """Initialize Databricks client connection."""
        try:
            host = os.getenv("DATABRICKS_HOST")
            token = os.getenv("DATABRICKS_TOKEN")

            if not host or not token:
                logger.warning("⚠️ Databricks credentials are not fully set. Databricks client will be unavailable.")
                return
            
            self.client = WorkspaceClient(host=host, token=token)
            
            # Test connection by listing clusters
            me = self.client.current_user.me()
            logger.info(f"✅ Connected to Databricks as user: {me.display_name} ({me.user_name})")
            self.connected = True

        except Exception as e:
            logger.warning(f"⚠️ Failed to connect to Databricks: {e}")
            self.connected = False

    # List clusters
    def list_clusters(self) -> list:
        """"List all clusters in the Databricks workspace."""
        if not self.connected:
            logger.warning("⚠️ Cannot list clusters because Databricks client is not connected.")
            return []
        
        try:
            clusters = self.client.clusters.list()
            return list(clusters)
        except Exception as e:
            logger.error(f"❌ Error listing clusters: {e}")
            return []
    
    # Get cluster status
    def get_cluster_status(self, cluster_id: str) -> Dict[str, Any]:
        """Get the status of a specific cluster"""
        if not self.connected:
            return {"status": "unavailable", "message": "Databricks client is not connected."}
        
        try:
            cluster = self.client.clusters.get(cluster_id)
            return {
                "cluster_id": cluster.cluster_id,
                "state": cluster.state,
                "driver": cluster.driver,
                "executors": cluster.executors,
                "spark_version": cluster.spark_version,
            }
        except Exception as e:
            logger.error(f"❌ Error getting cluster status for {cluster_id}: {e}")
            return {"status": "error", "message": str(e)}
        
    # List jobs
    def list_jobs(self) -> list:
        """List all jobs in the Databricks workspace."""
        if not self.connected:
            logger.warning(" ⚠️ Cannot list jobs because Databricks client is not connected.")
            return []
        
        try:
            jobs = self.client.jobs.list()
            return list(jobs)
        except Exception as e:
            logger.error(f"❌ Error listing jobs: {e}")
            return []
        
    # Get job runs
    def get_job_runs(self, job_id: int, limit: int = 10) -> list:
        """Get recent runs for a specific job."""
        if not self.connected:
            logger.warning("⚠️ Cannot get job runs because Databricks client is not connected.")
            return []
        
        try:
            runs = self.client.jobs.list_runs(job_id=job_id, limit=limit)
            return list(runs)
        except Exception as e:
            logger.error(f"❌ Error getting job runs for job {job_id}: {e}")
            return []
        
    def query_warehouse(self, sql: str) -> Dict[str, Any]:
        """Execute a SQL query on Databricks SQL Warehouse."""
        if not self.connected:
            return {"status": "unavailable", "message": "Databricks client is not connected."}
        
        try:
            # Use SQL warehouse API
            response = self.client.sql.execute(sql)
            return {
                "status": "success",
                "data": response
            }
        except Exception as e:
            logger.error(f"❌ Error executing SQL query: {e}")
            return {"status": "error", "message": str(e)}
        
    # Close connection
    def close(self):
        """Close the Databricks client connection."""
        if self.client:
            logger.info("🛑 Closing Databricks client connection.")

# Singleton instance
databricks_client = DatabricksClient()