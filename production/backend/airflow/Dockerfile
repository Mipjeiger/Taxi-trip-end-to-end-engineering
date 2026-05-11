FROM apache/airflow:2.8.0-python3.11

# Use the official environment variable method for most packages
ENV _PIP_ADDITIONAL_REQUIREMENTS=\
    apache-airflow-providers-postgres==6.5.1 \
    psycopg2-binary==2.9.9 \
    pandas==2.1.4 \
    pyarrow==14.0.1 \
    kafka-python==2.2.15 \
    SQLAlchemy==2.0.45

# Install system dependencies (as root before switching)
USER root
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    gcc \
    postgresql-client \
    git \
    && rm -rf /var/lib/apt/lists/*

# Switch to airflow user for pip installations
USER airflow

# Install databricks connector separately (sometimes has dependency issues)
RUN pip install --no-cache-dir databricks-sql-connector==1.0.0

ENV PYTHONPATH=/opt/airflow
WORKDIR /opt/airflow

# Copy custom entrypoint script
COPY --chown=airflow:airflow entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

# Use custom entrypoint to initialize database and create users
ENTRYPOINT ["/entrypoint.sh"]
CMD ["airflow", "webserver"]