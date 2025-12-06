# Autoscaling Metrics Collector

This script collects metrics from Docker containers and Prometheus every 20 seconds and outputs JSON format suitable for autoscaling decisions.

## Features

The script collects the following metrics per service:

### Resource Metrics (from Docker)
- **CPU Usage**: Percentage of CPU used
- **Memory Usage**: Memory used and limit in bytes, and percentage
- **Network I/O**: Network input/output
- **Block I/O**: Disk input/output

### Application Metrics (from Prometheus)
- **Request Rate**: Requests per second
- **Latency Percentiles**: P50, P95, P99 response times (in milliseconds)
- **Error Rate**: 5xx error rate (if available)

### Autoscaling Score
- Calculates a weighted score (0-1) based on:
  - CPU usage (40% weight)
  - Memory usage (30% weight)
  - Request rate (20% weight)
  - Latency (10% weight)
- Provides recommendation: `scale_up`, `scale_down`, or `maintain`

## Prerequisites

1. Python 3.6 or higher
2. Docker and docker-compose running
3. Prometheus running (optional, but recommended for full metrics)
4. Install Python dependencies:
   ```powershell
   pip install -r requirements.txt
   ```

## Usage

### Basic Usage
```powershell
cd deploy/docker-compose
python collect_autoscaling_metrics.py
```

### Save to File
```powershell
python collect_autoscaling_metrics.py > metrics_output.json
```

### Filter Specific Service (using jq on Linux/Mac)
```bash
python collect_autoscaling_metrics.py | jq '.services["front-end"]'
```

### Run in Background (Windows PowerShell)
```powershell
Start-Process python -ArgumentList "collect_autoscaling_metrics.py" -NoNewWindow
```

## Output Format

```json
{
  "timestamp": "2025-12-06T15:30:00.123456Z",
  "services": {
    "front-end": {
      "service_name": "front-end",
      "timestamp": "2025-12-06T15:30:00.123456Z",
      "resource_metrics": {
        "cpu_percent": 15.5,
        "memory_used_bytes": 52428800,
        "memory_limit_bytes": 1073741824,
        "memory_percent": 4.88,
        "network_io": "1.2MB / 800KB",
        "block_io": "0B / 0B"
      },
      "application_metrics": {
        "request_rate": 5.2,
        "request_duration_p50": 45.3,
        "request_duration_p95": 120.5,
        "request_duration_p99": 250.8,
        "error_rate": 0.01,
        "active_requests": null
      },
      "autoscaling_score": {
        "score": 0.425,
        "recommendation": "maintain",
        "factors": {
          "cpu_factor": 0.155,
          "memory_factor": 0.049,
          "request_rate_factor": 0.520,
          "latency_factor": 0.241
        }
      }
    }
  }
}
```

## Understanding the Metrics

### CPU Percent
- **0-50%**: Low load, consider scaling down
- **50-80%**: Normal load, maintain
- **80-100%**: High load, consider scaling up

### Memory Percent
- **0-60%**: Normal usage
- **60-80%**: Getting high, monitor closely
- **80-100%**: Critical, scale up immediately

### Request Rate
- Varies by service type
- Front-end typically has higher rates
- Database services have lower rates

### Latency (P95)
- **< 100ms**: Excellent
- **100-500ms**: Good
- **> 500ms**: Poor, consider scaling up

### Autoscaling Score
- **0.0-0.3**: Low load → `scale_down`
- **0.3-0.8**: Normal load → `maintain`
- **0.8-1.0**: High load → `scale_up`

## Troubleshooting

### Prometheus Not Available
The script will still work but application metrics will be `null`. Resource metrics from Docker will still be collected.

### Docker Stats Not Available
Make sure Docker is running and containers are up:
```powershell
docker-compose ps
```

### Python Module Not Found
Install dependencies:
```powershell
pip install requests
```

## Integration with Autoscaling

You can pipe this output to:
- Kubernetes HPA (Horizontal Pod Autoscaler)
- Custom autoscaling scripts
- Monitoring dashboards
- Alert systems

Example integration:
```python
import json
import subprocess

process = subprocess.Popen(
    ['python', 'collect_autoscaling_metrics.py'],
    stdout=subprocess.PIPE,
    text=True
)

for line in process.stdout:
    if line.strip():
        metrics = json.loads(line)
        for service, data in metrics['services'].items():
            if data['autoscaling_score']['recommendation'] == 'scale_up':
                # Trigger scaling action
                print(f"Scaling up {service}")
```

