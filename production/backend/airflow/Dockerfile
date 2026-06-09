FROM apache/airflow:2.10.5-python3.11

USER root
RUN apt-get update && apt-get install -y --no-install-recommends \
    postgresql-client \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

USER airflow

COPY --chown=airflow:airflow requirements.txt /opt/airflow/requirements.txt

# FIXED: Changed constraint URL to match your 2.10.5 base image perfectly
RUN pip install --no-cache-dir -r /opt/airflow/requirements.txt \
    --constraint "https://raw.githubusercontent.com/apache/airflow/constraints-2.10.5/constraints-3.11.txt"

ENV PYTHONPATH=/opt/airflow
WORKDIR /opt/airflow

COPY --chown=airflow:airflow entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

ENTRYPOINT ["/entrypoint.sh"]
CMD ["airflow", "webserver"]