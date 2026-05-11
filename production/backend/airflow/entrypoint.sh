#!/bin/bash
set -e

echo "Starting Airflow initialization..."

# Wait for database
echo "Waiting for database..."
for i in {1..30}; do
  if pg_isready -h airflow-db -U airflow > /dev/null 2>&1; then
    echo "Database is ready!"
    break
  fi
  echo "Waiting for database... ($i/30)"
  sleep 2
done

# Run migrations
echo "Running database migrations..."
airflow db migrate

# Create default user if it doesn't exist
echo "Creating default Airflow user..."
airflow users create \
  --username admin \
  --password admin \
  --firstname Admin \
  --lastname User \
  --email admin@airflow.com \
  --role Admin \
  2>/dev/null || echo "User already exists or creation skipped"

echo "Airflow initialization complete!"

# Execute the command passed to the container
exec "$@"
