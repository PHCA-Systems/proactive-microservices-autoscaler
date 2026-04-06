@echo off
echo ================================================================================
echo ML-DRIVEN AUTOSCALING SYSTEM - PRODUCTION MODE
echo ================================================================================
echo.

set MODE=production
cd ..

echo [1/3] Starting Sock Shop and Prometheus...
cd microservices-demo\deploy\docker-compose
docker-compose -f docker-compose.yml -f docker-compose.monitoring.yml up -d
cd ..\..\..

echo.
echo [2/3] Starting Kafka and ML services...
C:\Windows\System32\timeout.exe /t 45 /nobreak >nul
docker-compose -f docker-compose.ml.yml --profile production up -d

echo.
echo [3/3] Waiting for ML services to initialize (45 seconds)...
C:\Windows\System32\timeout.exe /t 45 /nobreak >nul

echo.
echo ================================================================================
echo SYSTEM STARTED - DISPLAYING SCALING DECISIONS
echo ================================================================================
echo.
echo Polling Interval: 30 seconds
echo Models: XGBoost, Random Forest, Logistic Regression
echo.
echo Each decision shows:
echo   - Service name (orders, carts, payment, etc.)
echo   - Each model's vote (SCALE UP or NO ACTION)
echo   - Model confidence percentage
echo   - Final decision based on majority voting
echo.
echo Press Ctrl+C to stop viewing (services will continue running)
echo To stop all services, run: stop-all.bat
echo.
echo ================================================================================
echo.

REM Display the authoritative scaler output in real-time
docker-compose -f docker-compose.ml.yml logs -f authoritative-scaler
