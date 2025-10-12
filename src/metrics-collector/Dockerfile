# Copyright The OpenTelemetry Authors
# SPDX-License-Identifier: Apache-2.0

FROM python:3.11-slim

WORKDIR /app

# Copy requirements and install Python dependencies
COPY src/metrics-collector/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY src/metrics-collector/app.py .

# Create non-root user
RUN useradd -m -u 1001 appuser && chown -R appuser:appuser /app
USER appuser

CMD ["python", "app.py"]