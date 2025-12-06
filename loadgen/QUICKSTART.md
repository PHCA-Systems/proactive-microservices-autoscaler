# LoadGenerator Quick Start Guide

## Installation

1. **Install Python dependencies**:
   ```bash
   pip install -r requirements.txt
   # Or install individually:
   pip install locust pandas numpy requests
   ```

2. **Ensure Sock Shop is running**:
   ```bash
   cd deploy/docker-compose
   docker-compose up -d
   ```

3. **Verify the application is accessible**:
   - Open browser: http://localhost
   - Should see Sock Shop homepage

## Quick Test

Run the example script:

```bash
python loadgen/example_usage.py
```

This will:
1. Generate load at 10 RPS for 25 seconds
2. Collect statistics
3. Run a workload sequence [5, 10, 20] RPS
4. Show results

## Basic Usage

```python
from loadgen.load_generator import LoadGenerator

# Initialize
lg = LoadGenerator(
    host='http://localhost',
    locustfile='loadgen/locustfile.py',
    duration=25
)

# Generate load
lg.generate_load(rps=10)

# Get statistics
stats = lg.read_load_statistics(rps=10)
print(stats)
```

## Output Files

After running, check:
- `logs/scratch/cola_lg.csv_stats.csv` - Aggregated statistics
- `logs/scratch/cola_lg.csv_stats_history.csv` - Time-series data
- `service_replicas_count.json` - Replica measurements

## Troubleshooting

### "locust: command not found"
```bash
pip install locust
```

### "No such file or directory: logs/scratch"
The directory is created automatically, but if it fails:
```bash
mkdir -p logs/scratch
```

### "Connection refused" errors
- Ensure Sock Shop is running: `docker-compose ps`
- Check the host URL is correct (default: http://localhost)

### Windows-specific issues
- Use `python` instead of `python3`
- Paths use forward slashes in Python code (works on Windows)

## Next Steps

- Read `LOADGEN_INTEGRATION.md` for detailed explanation
- Customize `locustfile.py` for your test scenarios
- Integrate with autoscaling logic using QoE scores

