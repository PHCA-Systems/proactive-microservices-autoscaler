Sock Shop Metrics Collection
=============================

USAGE
-----
python run_experiment.py --pattern <pattern> --duration <minutes> --output <filename.csv>

PATTERNS
--------
- constant : 50 users steady load
- ramp     : 10->150->10 users gradual
- step     : 50->200->100->300->50 users
- spike    : Base 10 with 30s spikes

EXAMPLES
--------
# 10-minute ramp test
python run_experiment.py --pattern ramp --duration 10 --output ramp_10min.csv

# 5-minute constant test (skip docker if already running)
python run_experiment.py --pattern constant --duration 5 --output constant_5min.csv --skip-docker

OUTPUT STRUCTURE
----------------
output/
  csv/          - All CSV files with metrics data
  logs/         - All log files (locust, collector)

EXPECTED ROWS
-------------
Duration × 2 polls/min × 7 services
- 1 min  = 14 rows
- 5 min  = 70 rows
- 10 min = 140 rows
- 30 min = 420 rows

CSV COLUMNS (13)
----------------
timestamp, service, request_rate_rps, error_rate_pct, 
p50_latency_ms, p95_latency_ms, p99_latency_ms,
cpu_usage_pct, memory_usage_mb, delta_rps, 
delta_p95_latency_ms, delta_cpu_usage_pct, sla_violated

SERVICES (7)
------------
front-end, carts, catalogue, orders, payment, shipping, user
