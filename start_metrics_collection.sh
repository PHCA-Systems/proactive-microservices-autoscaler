#!/bin/bash

# Start metrics collection for ML training data
# This script starts the metrics collector and streams the output

echo "Starting metrics collection for ML autoscaling training..."

# Create logs directory if it doesn't exist
mkdir -p logs

# Build and start the metrics collector
echo "Building metrics collector..."
docker-compose build metrics-collector

echo "Starting metrics collector..."
docker-compose up -d metrics-collector

# Wait a moment for the container to start
sleep 5

echo "Streaming metrics (press Ctrl+C to stop)..."
echo "Metrics format: {\"timestamp\": \"...\", \"service\": \"cart\", \"rps\": 120.4, \"cpu_percent\": 57.8, \"memory_mb\": 243.2, \"latency_p95_ms\": 42.1, ...}"
echo ""

# Stream the logs
python src/metrics-collector/stream_logs.py --output logs/training_data.jsonl

echo "Metrics collection stopped."