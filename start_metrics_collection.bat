@echo off
REM Start metrics collection for ML training data
REM This script starts the metrics collector and streams the output

echo Starting metrics collection for ML autoscaling training...

REM Create logs directory if it doesn't exist
if not exist logs mkdir logs

REM Build and start the metrics collector
echo Building metrics collector...
docker-compose build metrics-collector

echo Starting metrics collector...
docker-compose up -d metrics-collector

REM Wait a moment for the container to start
timeout /t 5 /nobreak >nul

echo Streaming metrics (press Ctrl+C to stop)...
echo Metrics format: {"timestamp": "...", "service": "cart", "rps": 120.4, "cpu_percent": 57.8, "memory_mb": 243.2, "latency_p95_ms": 42.1, ...}
echo.

REM Stream the logs
python src/metrics-collector/stream_logs.py --output logs/training_data.jsonl

echo Metrics collection stopped.