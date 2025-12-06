@echo off
REM Autoscaling Metrics Collector - Windows Batch File
REM This script runs the metrics collector

echo Installing Python dependencies...
pip install -r requirements.txt

echo.
echo Starting metrics collector...
echo Press Ctrl+C to stop
echo.

python collect_autoscaling_metrics.py

pause

