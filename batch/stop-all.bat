@echo off
echo Stopping all services...
echo.
cd ..
docker-compose -f docker-compose.ml.yml --profile production down
docker-compose -f docker-compose.ml.yml --profile development down

cd microservices-demo\deploy\docker-compose
docker-compose -f docker-compose.yml -f docker-compose.monitoring.yml down
cd ..\..\..

echo.
echo All services stopped.
