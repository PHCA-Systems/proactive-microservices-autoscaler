@echo off
echo ================================================================================
echo ML-DRIVEN AUTOSCALING SYSTEM - DEVELOPMENT MODE
echo ================================================================================
echo.

set MODE=development
cd ..

echo [1/3] Starting Sock Shop and Prometheus...
cd microservices-demo\deploy\docker-compose
docker-compose -f docker-compose.yml -f docker-compose.monitoring.yml up -d
cd ..\..\..

echo.
echo [2/3] Starting Kafka and Metrics Aggregator...
C:\Windows\System32\timeout.exe /t 30 /nobreak >nul
docker-compose -f docker-compose.ml.yml --profile development up -d

echo.
echo [3/3] Waiting for services to initialize (30 seconds)...
C:\Windows\System32\timeout.exe /t 30 /nobreak >nul

echo.
echo ================================================================================
echo SYSTEM STARTED - DISPLAYING METRICS COLLECTION
echo ================================================================================
echo.
echo Polling Interval: 30 seconds
echo Output: .\output\sockshop_metrics.csv
echo.
echo Collecting metrics for model retraining:
echo   - Request rate, error rate, latency percentiles
echo   - CPU usage, memory usage
echo   - Delta metrics (changes over time)
echo.
echo Press Ctrl+C to stop viewing (services will continue running)
echo To stop all services, run: stop-all.bat
echo.
echo ================================================================================
echo.

REM Display the metrics aggregator output in real-time
docker-compose -f docker-compose.ml.yml logs -f metrics-aggregator
