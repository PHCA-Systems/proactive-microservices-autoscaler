#!/usr/bin/env python3
"""
Real-time metrics collector for ML autoscaling training data.
Collects comprehensive service metrics and outputs structured JSON logs.
"""

import asyncio
import json
import logging
import time
from datetime import datetime
from typing import Dict, List, Optional
import aiohttp
import psutil
import os
from dataclasses import dataclass, asdict

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

@dataclass
class ServiceMetrics:
    """Structured metrics for a service"""
    timestamp: str
    service: str
    rps: float
    cpu_percent: float
    memory_mb: float
    latency_p95_ms: float
    latency_p50_ms: float
    latency_p99_ms: float
    error_rate: float
    active_connections: int
    queue_depth: int
    response_size_kb: float
    disk_io_mb_per_sec: float
    network_io_mb_per_sec: float
    replica_count: int
    target_cpu_utilization: float
    memory_utilization_percent: float
    gc_collections_per_sec: float
    thread_count: int
    heap_usage_mb: float

class MetricsCollector:
    def __init__(self):
        self.prometheus_url = os.getenv('PROMETHEUS_URL', 'http://prometheus:9090')
        self.services = [
            'cart', 'checkout', 'frontend', 'product-catalog', 
            'recommendation', 'payment', 'shipping', 'currency',
            'email', 'ad', 'accounting', 'fraud-detection'
        ]
        self.session = None
        
    async def start(self):
        """Initialize the metrics collector"""
        self.session = aiohttp.ClientSession()
        logger.info("Metrics collector started")
        
    async def stop(self):
        """Cleanup resources"""
        if self.session:
            await self.session.close()
            
    async def query_prometheus(self, query: str) -> Optional[Dict]:
        """Query Prometheus for metrics"""
        try:
            url = f"{self.prometheus_url}/api/v1/query"
            params = {'query': query}
            
            async with self.session.get(url, params=params) as response:
                if response.status == 200:
                    data = await response.json()
                    return data.get('data', {}).get('result', [])
                else:
                    logger.warning(f"Prometheus query failed: {response.status}")
                    return None
        except Exception as e:
            logger.error(f"Error querying Prometheus: {e}")
            return None
            
    async def get_service_rps(self, service: str) -> float:
        """Get requests per second for a service"""
        query = f'rate(http_requests_total{{service_name="{service}"}}[1m])'
        result = await self.query_prometheus(query)
        if result:
            return sum(float(item['value'][1]) for item in result)
        return 0.0
        
    async def get_service_latency(self, service: str, percentile: str) -> float:
        """Get latency percentile for a service"""
        query = f'histogram_quantile({percentile}, rate(http_request_duration_seconds_bucket{{service_name="{service}"}}[1m])) * 1000'
        result = await self.query_prometheus(query)
        if result and result[0]['value'][1] != 'NaN':
            return float(result[0]['value'][1])
        return 0.0
        
    async def get_service_cpu(self, service: str) -> float:
        """Get CPU usage percentage for a service"""
        query = f'rate(process_cpu_seconds_total{{service_name="{service}"}}[1m]) * 100'
        result = await self.query_prometheus(query)
        if result:
            return float(result[0]['value'][1])
        return 0.0
        
    async def get_service_memory(self, service: str) -> float:
        """Get memory usage in MB for a service"""
        query = f'process_resident_memory_bytes{{service_name="{service}"}} / 1024 / 1024'
        result = await self.query_prometheus(query)
        if result:
            return float(result[0]['value'][1])
        return 0.0
        
    async def get_service_error_rate(self, service: str) -> float:
        """Get error rate percentage for a service"""
        error_query = f'rate(http_requests_total{{service_name="{service}",status_code=~"5.."}}[1m])'
        total_query = f'rate(http_requests_total{{service_name="{service}"}}[1m])'
        
        error_result = await self.query_prometheus(error_query)
        total_result = await self.query_prometheus(total_query)
        
        if error_result and total_result:
            errors = sum(float(item['value'][1]) for item in error_result)
            total = sum(float(item['value'][1]) for item in total_result)
            return (errors / total * 100) if total > 0 else 0.0
        return 0.0
        
    async def get_service_connections(self, service: str) -> int:
        """Get active connections for a service"""
        query = f'http_server_active_requests{{service_name="{service}"}}'
        result = await self.query_prometheus(query)
        if result:
            return int(float(result[0]['value'][1]))
        return 0
        
    async def get_service_queue_depth(self, service: str) -> int:
        """Get queue depth for a service"""
        query = f'http_server_request_queue_size{{service_name="{service}"}}'
        result = await self.query_prometheus(query)
        if result:
            return int(float(result[0]['value'][1]))
        return 0
        
    async def get_service_response_size(self, service: str) -> float:
        """Get average response size in KB"""
        query = f'rate(http_response_size_bytes_sum{{service_name="{service}"}}[1m]) / rate(http_response_size_bytes_count{{service_name="{service}"}}[1m]) / 1024'
        result = await self.query_prometheus(query)
        if result and result[0]['value'][1] != 'NaN':
            return float(result[0]['value'][1])
        return 0.0
        
    async def get_service_disk_io(self, service: str) -> float:
        """Get disk I/O in MB/sec"""
        query = f'rate(process_io_storage_read_bytes_total{{service_name="{service}"}}[1m]) + rate(process_io_storage_written_bytes_total{{service_name="{service}"}}[1m]) / 1024 / 1024'
        result = await self.query_prometheus(query)
        if result:
            return float(result[0]['value'][1])
        return 0.0
        
    async def get_service_network_io(self, service: str) -> float:
        """Get network I/O in MB/sec"""
        query = f'rate(process_network_receive_bytes_total{{service_name="{service}"}}[1m]) + rate(process_network_transmit_bytes_total{{service_name="{service}"}}[1m]) / 1024 / 1024'
        result = await self.query_prometheus(query)
        if result:
            return float(result[0]['value'][1])
        return 0.0
        
    async def get_replica_count(self, service: str) -> int:
        """Get current replica count"""
        query = f'count(up{{service_name="{service}"}})'
        result = await self.query_prometheus(query)
        if result:
            return int(float(result[0]['value'][1]))
        return 1
        
    async def get_gc_collections(self, service: str) -> float:
        """Get garbage collection rate per second"""
        query = f'rate(process_gc_collections_total{{service_name="{service}"}}[1m])'
        result = await self.query_prometheus(query)
        if result:
            return float(result[0]['value'][1])
        return 0.0
        
    async def get_thread_count(self, service: str) -> int:
        """Get thread count for a service"""
        query = f'process_threads{{service_name="{service}"}}'
        result = await self.query_prometheus(query)
        if result:
            return int(float(result[0]['value'][1]))
        return 0
        
    async def get_heap_usage(self, service: str) -> float:
        """Get heap usage in MB"""
        query = f'process_heap_bytes{{service_name="{service}"}} / 1024 / 1024'
        result = await self.query_prometheus(query)
        if result:
            return float(result[0]['value'][1])
        return 0.0
        
    async def collect_service_metrics(self, service: str) -> ServiceMetrics:
        """Collect comprehensive metrics for a single service"""
        timestamp = datetime.utcnow().isoformat() + "Z"
        
        # Collect all metrics concurrently
        tasks = [
            self.get_service_rps(service),
            self.get_service_cpu(service),
            self.get_service_memory(service),
            self.get_service_latency(service, "0.95"),
            self.get_service_latency(service, "0.50"),
            self.get_service_latency(service, "0.99"),
            self.get_service_error_rate(service),
            self.get_service_connections(service),
            self.get_service_queue_depth(service),
            self.get_service_response_size(service),
            self.get_service_disk_io(service),
            self.get_service_network_io(service),
            self.get_replica_count(service),
            self.get_gc_collections(service),
            self.get_thread_count(service),
            self.get_heap_usage(service)
        ]
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Handle any exceptions and provide defaults
        safe_results = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                logger.warning(f"Error collecting metric {i} for {service}: {result}")
                safe_results.append(0.0 if i < 13 else 0)
            else:
                safe_results.append(result)
        
        memory_mb = safe_results[2]
        memory_limit = 500.0  # Assume 500MB limit, adjust based on your setup
        
        return ServiceMetrics(
            timestamp=timestamp,
            service=service,
            rps=safe_results[0],
            cpu_percent=safe_results[1],
            memory_mb=memory_mb,
            latency_p95_ms=safe_results[3],
            latency_p50_ms=safe_results[4],
            latency_p99_ms=safe_results[5],
            error_rate=safe_results[6],
            active_connections=safe_results[7],
            queue_depth=safe_results[8],
            response_size_kb=safe_results[9],
            disk_io_mb_per_sec=safe_results[10],
            network_io_mb_per_sec=safe_results[11],
            replica_count=safe_results[12],
            target_cpu_utilization=70.0,  # Target for autoscaling
            memory_utilization_percent=(memory_mb / memory_limit * 100) if memory_limit > 0 else 0.0,
            gc_collections_per_sec=safe_results[13],
            thread_count=safe_results[14],
            heap_usage_mb=safe_results[15]
        )
        
    async def collect_all_metrics(self) -> List[ServiceMetrics]:
        """Collect metrics for all services"""
        tasks = [self.collect_service_metrics(service) for service in self.services]
        return await asyncio.gather(*tasks, return_exceptions=True)
        
    def log_metrics(self, metrics: ServiceMetrics):
        """Log metrics in structured JSON format"""
        # Convert to dict and ensure all values are JSON serializable
        metrics_dict = asdict(metrics)
        
        # Round floating point numbers for cleaner logs
        for key, value in metrics_dict.items():
            if isinstance(value, float):
                metrics_dict[key] = round(value, 2)
                
        # Log as structured JSON
        print(json.dumps(metrics_dict, separators=(',', ':')))
        
    async def run_collection_loop(self, interval: int = 5):
        """Main collection loop"""
        logger.info(f"Starting metrics collection every {interval} seconds")
        
        while True:
            try:
                start_time = time.time()
                
                # Collect metrics for all services
                all_metrics = await self.collect_all_metrics()
                
                # Log each service's metrics
                for metrics in all_metrics:
                    if not isinstance(metrics, Exception):
                        self.log_metrics(metrics)
                    else:
                        logger.error(f"Failed to collect metrics: {metrics}")
                
                # Calculate sleep time to maintain interval
                elapsed = time.time() - start_time
                sleep_time = max(0, interval - elapsed)
                
                if sleep_time > 0:
                    await asyncio.sleep(sleep_time)
                    
            except KeyboardInterrupt:
                logger.info("Shutting down metrics collector")
                break
            except Exception as e:
                logger.error(f"Error in collection loop: {e}")
                await asyncio.sleep(interval)

async def main():
    """Main entry point"""
    collector = MetricsCollector()
    
    try:
        await collector.start()
        
        # Get collection interval from environment
        interval = int(os.getenv('COLLECTION_INTERVAL', '5'))
        
        await collector.run_collection_loop(interval)
        
    finally:
        await collector.stop()

if __name__ == "__main__":
    asyncio.run(main())