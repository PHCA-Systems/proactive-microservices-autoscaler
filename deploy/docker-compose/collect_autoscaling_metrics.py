#!/usr/bin/env python3
"""
Autoscaling Metrics Collector
Collects metrics from Docker containers and Prometheus every 20 seconds
and outputs JSON format suitable for autoscaling decisions.
"""

import json
import time
import subprocess
import sys
import requests
from datetime import datetime, timezone
from typing import Dict, List, Optional

# Service names mapping (Docker Compose service names)
SERVICES = [
    'front-end',
    'edge-router',
    'catalogue',
    'catalogue-db',
    'carts',
    'carts-db',
    'orders',
    'orders-db',
    'payment',
    'shipping',
    'user',
    'user-db',
    'queue-master',
    'rabbitmq'
]

# Prometheus configuration
PROMETHEUS_URL = "http://localhost:9090"
PROMETHEUS_QUERY_ENDPOINT = f"{PROMETHEUS_URL}/api/v1/query"

# Service to Prometheus job mapping
SERVICE_TO_JOB = {
    'front-end': 'frontend',
    'edge-router': 'frontend',
    'catalogue': 'catalogue',
    'carts': 'cart',
    'orders': 'orders',
    'payment': 'payment',
    'shipping': 'shipping',
    'user': 'user',
    'queue-master': 'queue-master'
}


def get_docker_stats() -> Dict[str, Dict]:
    """Get Docker container stats using docker stats command."""
    try:
        # Get stats in JSON format, no stream
        result = subprocess.run(
            ['docker', 'stats', '--no-stream', '--format', 'json'],
            capture_output=True,
            text=True,
            timeout=10
        )
        
        if result.returncode != 0:
            print(f"Error getting Docker stats: {result.stderr}", file=sys.stderr)
            return {}
        
        stats = {}
        for line in result.stdout.strip().split('\n'):
            if not line:
                continue
            try:
                container_data = json.loads(line)
                container_name = container_data.get('Name', '')
                
                # Extract service name from container name
                # Handle patterns like: "docker-compose-front-end-1", "docker-compose-catalogue-db-1"
                for service in SERVICES:
                    # Try multiple matching patterns
                    service_variants = [
                        service.replace('-', '_'),  # front-end -> front_end
                        service,  # front-end
                        service.replace('-', ''),  # front-end -> frontend
                    ]
                    
                    # Also handle database containers (catalogue-db -> catalogue-db or catalogue_db)
                    if '-db' in service:
                        service_variants.append(service.replace('-db', '_db'))
                        service_variants.append(service.replace('-db', 'db'))
                    
                    matched = False
                    for variant in service_variants:
                        if variant in container_name:
                            matched = True
                            break
                    
                    if matched:
                        # Parse CPU percentage
                        cpu_percent = container_data.get('CPUPerc', '0%').rstrip('%')
                        try:
                            cpu_percent = float(cpu_percent)
                        except ValueError:
                            cpu_percent = 0.0
                        
                        # Parse memory
                        mem_usage = container_data.get('MemUsage', '0B / 0B')
                        mem_parts = mem_usage.split(' / ')
                        mem_used_str = mem_parts[0] if len(mem_parts) > 0 else '0B'
                        mem_limit_str = mem_parts[1] if len(mem_parts) > 1 else '0B'
                        
                        # Parse memory percentage
                        mem_percent = container_data.get('MemPerc', '0%').rstrip('%')
                        try:
                            mem_percent = float(mem_percent)
                        except ValueError:
                            mem_percent = 0.0
                        
                        # Parse network I/O
                        net_io = container_data.get('NetIO', '0B / 0B')
                        block_io = container_data.get('BlockIO', '0B / 0B')
                        
                        stats[service] = {
                            'container_name': container_name,
                            'cpu_percent': cpu_percent,
                            'memory_used': mem_used_str,
                            'memory_limit': mem_limit_str,
                            'memory_percent': mem_percent,
                            'network_io': net_io,
                            'block_io': block_io
                        }
                        break  # Found the service, move to next container
            except json.JSONDecodeError:
                continue
        
        return stats
    except Exception as e:
        print(f"Error in get_docker_stats: {e}", file=sys.stderr)
        return {}


def parse_bytes(size_str: str) -> float:
    """Convert size string (e.g., '1.5MiB', '87.9kB') to bytes."""
    if not size_str or size_str == '0B':
        return 0.0
    
    size_str = size_str.strip()
    
    # Normalize to uppercase for matching, but preserve original for parsing
    multipliers = {
        'B': 1,
        'KB': 1024,
        'MB': 1024**2,
        'GB': 1024**3,
        'TB': 1024**4,
        'KiB': 1024,
        'MiB': 1024**2,
        'GiB': 1024**3,
        'TiB': 1024**4,
        # Handle lowercase variants
        'kb': 1024,
        'mb': 1024**2,
        'gb': 1024**3,
        'tb': 1024**4,
        'kib': 1024,
        'mib': 1024**2,
        'gib': 1024**3,
        'tib': 1024**4
    }
    
    # Try to match units (case-insensitive)
    size_upper = size_str.upper()
    for unit, multiplier in multipliers.items():
        unit_upper = unit.upper()
        if size_upper.endswith(unit_upper):
            try:
                # Extract the number part
                num_str = size_str[:-len(unit)]
                return float(num_str) * multiplier
            except ValueError:
                return 0.0
    
    # Try to parse as plain number
    try:
        return float(size_str)
    except ValueError:
        return 0.0


def query_prometheus(query: str) -> Optional[float]:
    """Query Prometheus and return the first value."""
    try:
        response = requests.get(
            PROMETHEUS_QUERY_ENDPOINT,
            params={'query': query},
            timeout=5
        )
        if response.status_code == 200:
            data = response.json()
            if data['status'] == 'success' and data['data']['result']:
                value = data['data']['result'][0]['value'][1]
                return float(value)
        return None
    except Exception as e:
        # Prometheus might not be available, that's okay
        return None


def get_prometheus_metrics(service: str) -> Dict:
    """Get application metrics from Prometheus for a service."""
    metrics = {
        'request_rate': None,
        'request_duration_p50': None,
        'request_duration_p95': None,
        'request_duration_p99': None,
        'error_rate': None,
        'active_requests': None
    }
    
    job = SERVICE_TO_JOB.get(service)
    if not job:
        return metrics
    
    # Request rate (requests per second)
    query = f'rate(request_duration_seconds_count{{job="{job}"}}[1m])'
    value = query_prometheus(query)
    if value is not None:
        metrics['request_rate'] = round(value, 2)
    
    # P50 latency
    query = f'histogram_quantile(0.50, rate(request_duration_seconds_bucket{{job="{job}"}}[1m]))'
    value = query_prometheus(query)
    if value is not None:
        metrics['request_duration_p50'] = round(value * 1000, 2)  # Convert to ms
    
    # P95 latency
    query = f'histogram_quantile(0.95, rate(request_duration_seconds_bucket{{job="{job}"}}[1m]))'
    value = query_prometheus(query)
    if value is not None:
        metrics['request_duration_p95'] = round(value * 1000, 2)  # Convert to ms
    
    # P99 latency
    query = f'histogram_quantile(0.99, rate(request_duration_seconds_bucket{{job="{job}"}}[1m]))'
    value = query_prometheus(query)
    if value is not None:
        metrics['request_duration_p99'] = round(value * 1000, 2)  # Convert to ms
    
    # Error rate (if available)
    query = f'rate(http_requests_total{{job="{job}",status=~"5.."}}[1m])'
    value = query_prometheus(query)
    if value is not None:
        metrics['error_rate'] = round(value, 2)
    
    return metrics


def collect_metrics() -> Dict:
    """Collect all metrics for all services."""
    timestamp = datetime.now(timezone.utc).isoformat()
    
    # Get Docker stats
    docker_stats = get_docker_stats()
    
    # Collect metrics for each service
    services_metrics = {}
    
    for service in SERVICES:
        service_metrics = {
            'service_name': service,
            'timestamp': timestamp,
            'resource_metrics': {},
            'application_metrics': {}
        }
        
        # Add Docker stats if available
        if service in docker_stats:
            docker_data = docker_stats[service]
            service_metrics['resource_metrics'] = {
                'cpu_percent': docker_data['cpu_percent'],
                'memory_used_bytes': parse_bytes(docker_data['memory_used']),
                'memory_limit_bytes': parse_bytes(docker_data['memory_limit']),
                'memory_percent': docker_data['memory_percent'],
                'network_io': docker_data['network_io'],
                'block_io': docker_data['block_io']
            }
        
        # Add Prometheus metrics if available
        prom_metrics = get_prometheus_metrics(service)
        service_metrics['application_metrics'] = prom_metrics
        
        # Calculate autoscaling score (simple heuristic)
        autoscaling_score = calculate_autoscaling_score(
            service_metrics['resource_metrics'],
            service_metrics['application_metrics']
        )
        service_metrics['autoscaling_score'] = autoscaling_score
        
        services_metrics[service] = service_metrics
    
    return {
        'timestamp': timestamp,
        'services': services_metrics
    }


def calculate_autoscaling_score(resource_metrics: Dict, app_metrics: Dict) -> Dict:
    """Calculate a simple autoscaling score based on metrics."""
    score = 0.0
    factors = {}
    
    # CPU factor (0-1, higher = more load)
    cpu_percent = resource_metrics.get('cpu_percent', 0)
    cpu_factor = min(cpu_percent / 100.0, 1.0)
    factors['cpu_factor'] = round(cpu_factor, 3)
    
    # Memory factor
    mem_percent = resource_metrics.get('memory_percent', 0)
    mem_factor = min(mem_percent / 100.0, 1.0)
    factors['memory_factor'] = round(mem_factor, 3)
    
    # Request rate factor (normalized, assuming >10 req/s is high)
    request_rate = app_metrics.get('request_rate', 0) or 0
    rate_factor = min(request_rate / 10.0, 1.0)
    factors['request_rate_factor'] = round(rate_factor, 3)
    
    # Latency factor (P95 > 500ms is concerning)
    latency_p95 = app_metrics.get('request_duration_p95', 0) or 0
    latency_factor = min(latency_p95 / 500.0, 1.0)
    factors['latency_factor'] = round(latency_factor, 3)
    
    # Weighted average
    score = (cpu_factor * 0.4 + mem_factor * 0.3 + rate_factor * 0.2 + latency_factor * 0.1)
    
    # Recommendation
    if score > 0.8:
        recommendation = "scale_up"
    elif score < 0.3:
        recommendation = "scale_down"
    else:
        recommendation = "maintain"
    
    return {
        'score': round(score, 3),
        'recommendation': recommendation,
        'factors': factors
    }


def main():
    """Main loop - collect and print metrics every 20 seconds."""
    print("Starting Autoscaling Metrics Collector...", file=sys.stderr)
    print("Collecting metrics every 20 seconds...", file=sys.stderr)
    print("Press Ctrl+C to stop\n", file=sys.stderr)
    
    try:
        while True:
            metrics = collect_metrics()
            
            # Print JSON to stdout
            print(json.dumps(metrics, indent=2))
            print()  # Empty line for readability
            
            # Wait 20 seconds
            time.sleep(20)
            
    except KeyboardInterrupt:
        print("\nStopping metrics collector...", file=sys.stderr)
        sys.exit(0)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == '__main__':
    main()

