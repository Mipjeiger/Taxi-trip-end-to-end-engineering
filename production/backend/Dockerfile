from python:3.11-slim

WORKDIR /app

# Install system dependencies including OpenMP for XGBoost/LightGBM
RUN apt-get update && apt-get install -y --no-install-recommends \
    postgresql-client \
    curl \
    libgomp1 \
    && rm -rf /var/lib/apt/lists/*

# Copy wheels from the builder stage
COPY requirements.txt .

# Install Python dependencies from wheels
RUN pip install --no-cache-dir \
    --default-timeout=1000 \
    --retries 3 \
    -r requirements.txt \
    && rm -rf /root/.cache/pip

# Copy the application code
COPY . .

# Expose the application port
EXPOSE 8000

# Run with Uvicorn
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]