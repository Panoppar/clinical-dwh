FROM python:3.12-slim

# default-mysql-client provides the `mysql` CLI used to execute the layered
# *.sql DDL/DML scripts (multi-statement files are simplest to run via the
# real client rather than hand-rolling statement splitting in Python).
RUN apt-get update \
    && apt-get install -y --no-install-recommends default-mysql-client \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY run_pipeline.py extract_load_bronze.py extract_load_external_reference.py ./

# sql/ is bind-mounted at runtime (see docker-compose.yml) so SQL edits
# don't require an image rebuild.
CMD ["python", "run_pipeline.py"]
