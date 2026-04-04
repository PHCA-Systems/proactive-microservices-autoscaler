@echo off
echo ================================================================================
echo RUNNING LOAD TEST ON SOCK SHOP
echo ================================================================================
echo.
echo This will generate traffic to trigger SLA violations and SCALE UP decisions
echo.

cd ..

echo Select load pattern:
echo   1. Constant load (50 users, 10 minutes)
echo   2. Ramp load (gradual increase, 15 minutes)
echo   3. Spike load (sudden burst, 10 minutes)
echo   4. Custom
echo.

set /p choice="Enter choice (1-4): "

if "%choice%"=="1" (
    echo.
    echo Running CONSTANT load test...
    python metrics-collection/run_experiment.py --pattern constant --duration 10 --skip-docker
) else if "%choice%"=="2" (
    echo.
    echo Running RAMP load test...
    python metrics-collection/run_experiment.py --pattern ramp --duration 15 --skip-docker
) else if "%choice%"=="3" (
    echo.
    echo Running SPIKE load test...
    python metrics-collection/run_experiment.py --pattern spike --duration 10 --skip-docker
) else if "%choice%"=="4" (
    set /p duration="Enter duration in minutes: "
    set /p pattern="Enter pattern (constant/ramp/spike/step): "
    echo.
    echo Running %pattern% load test for %duration% minutes...
    python metrics-collection/run_experiment.py --pattern %pattern% --duration %duration% --skip-docker
) else (
    echo Invalid choice. Exiting.
    pause
    exit /b 1
)

echo.
echo ================================================================================
echo Load test complete!
echo ================================================================================
echo.
echo Check the authoritative scaler output to see SCALE UP decisions
echo.
pause
