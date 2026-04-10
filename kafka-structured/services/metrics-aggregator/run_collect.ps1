$env:MODE = "development"
$env:PROMETHEUS_URL = "http://localhost:9090"
$env:POLL_INTERVAL_SEC = "30"
$env:OUTPUT_DIR = "D:\Projects\Grad\PHCA\kafka-structured\services\metrics-aggregator\output"

& "D:\Projects\Grad\PHCA\kafka-structured\services\metrics-aggregator\venv\Scripts\python.exe" `
  "D:\Projects\Grad\PHCA\kafka-structured\services\metrics-aggregator\app.py"
