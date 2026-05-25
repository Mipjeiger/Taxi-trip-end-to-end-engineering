import React, { useState, useEffect } from 'react';
import axios from 'axios';

interface DatabricksStatus {
    connected: boolean;
    clusters: { total: number; running: number };
    jobs: { total: number };
}

export const DatabricksPanel: React.FC = () => {
    const [status, setStatus ] = useState<DatabricksStatus | null>(null);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        const fetchDatabricks = async () => {
            try {
                const response = await axios.get('/api/databricks/dashboard');
                setStatus(response.data);
            } catch(error) {
                console.error('Error fetching Databricks status:', error);
            } finally {
                setLoading(false);
            }
        };

        fetchDatabricks();
        const interval = setInterval(fetchDatabricks, 30000); // Refresh every 30 seconds
        return () => clearInterval(interval);
    }, []);

    if (loading) return <div>Loading Databricks...</div>;
    if (!status?.connected) return <div>⚠️ Error loading Databricks status (unavailable).</div>;

    return (
    <div className="databricks-panel">
      <h3>Databricks Status</h3>
      <div className="stats">
        <div>Clusters: {status.clusters.running}/{status.clusters.total} running</div>
        <div>Jobs: {status.jobs.total} total</div>
      </div>
    </div>
  );
};