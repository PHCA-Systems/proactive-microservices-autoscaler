"""
Kubernetes utilities for LoadGenerator.
This module provides functions to interact with Kubernetes/Docker Compose deployments.
"""

import subprocess
import json
import sys
import os
from typing import Dict, Optional
import pandas as pd

def get_current_deployments() -> Dict:
    """
    Get current deployment replicas from Docker Compose.
    Returns a dictionary mapping service names to replica counts.
    """
    try:
        # For Docker Compose, we check running containers
        result = subprocess.run(
            ['docker-compose', 'ps', '--format', 'json'],
            capture_output=True,
            text=True,
            cwd=os.path.join(os.path.dirname(__file__), '..', 'deploy', 'docker-compose')
        )
        
        if result.returncode != 0:
            # Try alternative: docker ps with filtering
            result = subprocess.run(
                ['docker', 'ps', '--format', '{{.Names}}'],
                capture_output=True,
                text=True
            )
        
        deployments = {}
        if result.returncode == 0:
            # Count containers per service
            for line in result.stdout.strip().split('\n'):
                if not line:
                    continue
                # Extract service name from container name
                # Format: docker-compose-front-end-1 -> front-end
                container_name = line.strip()
                for service in ['front-end', 'edge-router', 'catalogue', 'carts', 'orders', 
                               'payment', 'shipping', 'user', 'queue-master', 'rabbitmq']:
                    if service.replace('-', '_') in container_name or service in container_name:
                        deployments[service] = deployments.get(service, 0) + 1
                        break
        
        return deployments
    except Exception as e:
        print(f"Error getting deployments: {e}", file=sys.stderr)
        return {}


def get_pod_statistics() -> pd.DataFrame:
    """
    Get pod/container statistics (CPU, memory) from Docker.
    Returns a pandas DataFrame with utilization metrics.
    """
    try:
        # Use docker stats to get container metrics
        result = subprocess.run(
            ['docker', 'stats', '--no-stream', '--format', 
             '{{.Name}},{{.CPUPerc}},{{.MemUsage}},{{.MemPerc}}'],
            capture_output=True,
            text=True,
            timeout=10
        )
        
        if result.returncode != 0:
            return pd.DataFrame()
        
        data = []
        for line in result.stdout.strip().split('\n'):
            if not line or ',' not in line:
                continue
            parts = line.split(',')
            if len(parts) >= 4:
                container_name = parts[0]
                cpu_percent = parts[1].rstrip('%')
                mem_usage = parts[2]
                mem_percent = parts[3].rstrip('%')
                
                # Extract service name
                service_name = container_name
                for service in ['front-end', 'edge-router', 'catalogue', 'carts', 'orders',
                               'payment', 'shipping', 'user', 'queue-master', 'rabbitmq']:
                    if service.replace('-', '_') in container_name or service in container_name:
                        service_name = service
                        break
                
                try:
                    data.append({
                        'service': service_name,
                        'container': container_name,
                        'cpu_percent': float(cpu_percent) if cpu_percent else 0.0,
                        'memory_usage': mem_usage,
                        'memory_percent': float(mem_percent) if mem_percent else 0.0
                    })
                except ValueError:
                    continue
        
        return pd.DataFrame(data)
    except Exception as e:
        print(f"Error getting pod statistics: {e}", file=sys.stderr)
        return pd.DataFrame()


def get_kubernetes_deployments() -> Dict:
    """
    Alternative method for Kubernetes deployments.
    Uses kubectl to get deployment replicas.
    """
    try:
        result = subprocess.run(
            ['kubectl', 'get', 'deployments', '-o', 'json', '-n', 'sock-shop'],
            capture_output=True,
            text=True,
            timeout=10
        )
        
        if result.returncode != 0:
            return {}
        
        data = json.loads(result.stdout)
        deployments = {}
        
        for item in data.get('items', []):
            name = item['metadata']['name']
            replicas = item['spec'].get('replicas', 0)
            ready_replicas = item['status'].get('readyReplicas', 0)
            deployments[name] = {
                'desired': replicas,
                'ready': ready_replicas
            }
        
        return deployments
    except Exception as e:
        print(f"Error getting Kubernetes deployments: {e}", file=sys.stderr)
        return {}

