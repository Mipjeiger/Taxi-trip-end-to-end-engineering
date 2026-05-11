FROM apache/airflow:2.8.0-python3.11

# Install additional dependencies
USER root

RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    g++ \
    libpq-dev \
    curl \
    git \
    && rm -rf /var/lib/apt/lists/*

USER airflow

# Copy requirements file
COPY requirements.txt /tmp/requirements.txt

# Install Python packages
RUN pip install --no-cache-dir -r /tmp/requirements.txt

# Initialize Airflow database
RUN airflow db init || true

WORKDIR /app/airflow
