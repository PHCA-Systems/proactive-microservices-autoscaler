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
    """Structured metrics for a service - optimized for ML training"""
    # Timestamp and identification
    timestamp: str
    service: str
    
    # Performance Metrics
    rps: float
    latency_p50_ms: float
    latency_p95_ms: float
    latency_p99_ms: float
    latency_mean_ms: float
    error_rate: float
    success_rate: float
    
    # Resource Utilization
    cpu_percent: float
    memory_mb: float
    memory_utilization_percent: float
    disk_read_mb_per_sec: float
    disk_write_mb_per_sec: float
    disk_io_mb_per_sec: float
    network_receive_mb_per_sec: float
    network_transmit_mb_per_sec: float
    network_io_mb_per_sec: float
    
    # Application Metrics
    active_connections: int
    queue_depth: int
    response_size_kb: float
    request_size_kb: float
    thread_count: int
    heap_usage_mb: float
    gc_collections_per_sec: float
    gc_pause_time_ms: float
    
    # Scaling Context
    replica_count: int
    target_cpu_utilization: float
    target_memory_utilization: float
    
    # Derived Metrics for ML
    requests_per_connection: float
    avg_response_time_ms: float
    throughput_mb_per_sec: float
    resource_efficiency_score: float

class MetricsCollector:
    def __init__(self):
        self.prometheus_url = os.getenv('PROMETHEUS_URL', 'http://prometheus:9090')
        self.services = [
            'cart', 'checkout', 'frontend', 'product-catalog', 
            'recommendation', 'payment', 'shipping', 'currency',
            'email', 'ad', 'accounting', 'fraud-detection'
        ]
        self.session = None
        # Use 2m window for rate calculations to ensure enough data points
        self.rate_window = '2m'
        
    async def start(self):
        """Initialize the metrics collector"""
        self.session = aiohttp.ClientSession()
        logger.info("Metrics collector started")
        
    async def stop(self):
        """Cleanup resources"""
        if self.session:
            await self.session.close()
            
    async def query_prometheus(self, query: str) -> Optional[List]:
        """Query Prometheus for metrics"""
        try:
            url = f"{self.prometheus_url}/api/v1/query"
            params = {'query': query}
            
            async with self.session.get(url, params=params, timeout=aiohttp.ClientTimeout(total=10)) as response:
                if response.status == 200:
                    data = await response.json()
                    result = data.get('data', {}).get('result', [])
                    return result
                else:
                    logger.warning(f"Prometheus query failed: {response.status} for query: {query[:100]}")
                    return []
        except asyncio.TimeoutError:
            logger.error(f"Timeout querying Prometheus: {query[:100]}")
            return []
        except Exception as e:
            logger.error(f"Error querying Prometheus: {e}, query: {query[:100]}")
            return []
            
    async def get_service_rps(self, service: str) -> float:
        """Get requests per second for a service"""
        # Try http_server_duration_milliseconds_count (most common)
        query = f'sum(rate(http_server_duration_milliseconds_count{{service_name="{service}"}}[{self.rate_window}]))'
        result = await self.query_prometheus(query)
        if result and len(result) > 0:
            value = result[0]['value'][1]
            if value != 'NaN':
                return float(value)
        
        # Fallback to http_server_request_duration_seconds_count
        query = f'sum(rate(http_server_request_duration_seconds_count{{service_name="{service}"}}[{self.rate_window}]))'
        result = await self.query_prometheus(query)
        if result and len(result) > 0:
            value = result[0]['value'][1]
            if value != 'NaN':
                return float(value)
        
        # Fallback to RPC metrics for gRPC services
        query = f'sum(rate(rpc_server_duration_milliseconds_count{{service_name="{service}"}}[{self.rate_window}]))'
        result = await self.query_prometheus(query)
        if result and len(result) > 0:
            value = result[0]['value'][1]
            if value != 'NaN':
                return float(value)
        
        return 0.0
        
    async def get_service_latency(self, service: str, percentile: str) -> float:
        """Get latency percentile for a service"""
        # Try http_server_duration_milliseconds_bucket (most common, already in ms)
        query = f'histogram_quantile({percentile}, sum(rate(http_server_duration_milliseconds_bucket{{service_name="{service}"}}[{self.rate_window}])) by (le))'
        result = await self.query_prometheus(query)
        if result and len(result) > 0:
            value = result[0]['value'][1]
            if value != 'NaN':
                return float(value)
        
        # Fallback to http_server_request_duration_seconds_bucket (convert to ms)
        query = f'histogram_quantile({percentile}, sum(rate(http_server_request_duration_seconds_bucket{{service_name="{service}"}}[{self.rate_window}])) by (le)) * 1000'
        result = await self.query_prometheus(query)
        if result and len(result) > 0:
            value = result[0]['value'][1]
            if value != 'NaN':
                return float(value)
        
        # Fallback to RPC metrics for gRPC services
        query = f'histogram_quantile({percentile}, sum(rate(rpc_server_duration_milliseconds_bucket{{service_name="{service}"}}[{self.rate_window}])) by (le))'
        result = await self.query_prometheus(query)
        if result and len(result) > 0:
            value = result[0]['value'][1]
            if value != 'NaN':
                return float(value)
        
        return 0.0
        
    async def get_service_cpu(self, service: str) -> float:
        """Get CPU usage percentage for a service"""
        # Try process CPU metrics
        query = f'rate(process_cpu_seconds_total{{service_name="{service}"}}[{self.rate_window}]) * 100'
        result = await self.query_prometheus(query)
        if result and len(result) > 0:
            value = result[0]['value'][1]
            if value != 'NaN':
                return float(value)
        
        # Fallback to runtime CPU metrics
        query = f'rate(runtime_cpuTime{{service_name="{service}"}}[{self.rate_window}]) * 100'
        result = await self.query_prometheus(query)
        if result and len(result) > 0:
            value = result[0]['value'][1]
            if value != 'NaN':
                return float(value)
        
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
        # Try http_server_duration_milliseconds with status code (most common)
        error_query = f'sum(rate(http_server_duration_milliseconds_count{{service_name="{service}",http_status_code=~"5.."}}[{self.rate_window}]))'
        total_query = f'sum(rate(http_server_duration_milliseconds_count{{service_name="{service}"}}[{self.rate_window}]))'
        
        error_result = await self.query_prometheus(error_query)
        total_result = await self.query_prometheus(total_query)
        
        errors = 0.0
        total = 0.0
        
        if error_result and len(error_result) > 0:
            value = error_result[0]['value'][1]
            if value != 'NaN':
                errors = float(value)
        
        if total_result and len(total_result) > 0:
            value = total_result[0]['value'][1]
            if value != 'NaN':
                total = float(value)
        
        # If no data from milliseconds metrics, try seconds metrics
        if total == 0.0:
            error_query = f'sum(rate(http_server_request_duration_seconds_count{{service_name="{service}",http_response_status_code=~"5.."}}[{self.rate_window}]))'
            total_query = f'sum(rate(http_server_request_duration_seconds_count{{service_name="{service}"}}[{self.rate_window}]))'
            
            error_result = await self.query_prometheus(error_query)
            total_result = await self.query_prometheus(total_query)
            
            if error_result and len(error_result) > 0:
                value = error_result[0]['value'][1]
                if value != 'NaN':
                    errors = float(value)
            
            if total_result and len(total_result) > 0:
                value = total_result[0]['value'][1]
                if value != 'NaN':
                    total = float(value)
        
        return (errors / total * 100) if total > 0 else 0.0
        
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
        query = f'rate(http_server_response_body_size_sum{{service_name="{service}"}}[{self.rate_window}]) / rate(http_server_response_body_size_count{{service_name="{service}"}}[{self.rate_window}]) / 1024'
        result = await self.query_prometheus(query)
        if result and len(result) > 0:
            value = result[0]['value'][1]
            if value != 'NaN':
                return float(value)
        return 0.0
        
    async def get_service_disk_read(self, service: str) -> float:
        """Get disk read I/O in MB/sec"""
        query = f'rate(process_io_storage_read_bytes_total{{service_name="{service}"}}[{self.rate_window}]) / 1024 / 1024'
        result = await self.query_prometheus(query)
        if result:
            return float(result[0]['value'][1])
        return 0.0
        
    async def get_service_disk_write(self, service: str) -> float:
        """Get disk write I/O in MB/sec"""
        query = f'rate(process_io_storage_written_bytes_total{{service_name="{service}"}}[{self.rate_window}]) / 1024 / 1024'
        result = await self.query_prometheus(query)
        if result:
            return float(result[0]['value'][1])
        return 0.0
        
    async def get_service_disk_io(self, service: str) -> float:
        """Get total disk I/O in MB/sec"""
        read_io = await self.get_service_disk_read(service)
        write_io = await self.get_service_disk_write(service)
        return read_io + write_io
        
    async def get_service_network_receive(self, service: str) -> float:
        """Get network receive I/O in MB/sec"""
        query = f'rate(process_network_receive_bytes_total{{service_name="{service}"}}[{self.rate_window}]) / 1024 / 1024'
        result = await self.query_prometheus(query)
        if result:
            return float(result[0]['value'][1])
        return 0.0
        
    async def get_service_network_transmit(self, service: str) -> float:
        """Get network transmit I/O in MB/sec"""
        query = f'rate(process_network_transmit_bytes_total{{service_name="{service}"}}[{self.rate_window}]) / 1024 / 1024'
        result = await self.query_prometheus(query)
        if result:
            return float(result[0]['value'][1])
        return 0.0
        
    async def get_service_network_io(self, service: str) -> float:
        """Get total network I/O in MB/sec"""
        receive_io = await self.get_service_network_receive(service)
        transmit_io = await self.get_service_network_transmit(service)
        return receive_io + transmit_io
        
    async def get_replica_count(self, service: str) -> int:
        """Get current replica count"""
        query = f'count(up{{service_name="{service}"}})'
        result = await self.query_prometheus(query)
        if result:
            return int(float(result[0]['value'][1]))
        return 1
        
    async def get_gc_collections(self, service: str) -> float:
        """Get garbage collection rate per second"""
        query = f'rate(process_gc_collections_total{{service_name="{service}"}}[{self.rate_window}])'
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
        
    async def get_gc_pause_time(self, service: str) -> float:
        """Get average GC pause time in ms"""
        query = f'rate(process_gc_pause_seconds_total{{service_name="{service}"}}[{self.rate_window}]) * 1000'
        result = await self.query_prometheus(query)
        if result:
            return float(result[0]['value'][1])
        return 0.0
        
    async def get_request_size(self, service: str) -> float:
        """Get average request size in KB"""
        query = f'rate(http_server_request_body_size_sum{{service_name="{service}"}}[{self.rate_window}]) / rate(http_server_request_body_size_count{{service_name="{service}"}}[{self.rate_window}]) / 1024'
        result = await self.query_prometheus(query)
        if result and len(result) > 0:
            value = result[0]['value'][1]
            if value != 'NaN':
                return float(value)
        return 0.0
        
    async def get_latency_mean(self, service: str) -> float:
        """Get mean latency for a service"""
        # Try http_server_duration_milliseconds (most common, already in ms)
        query = f'rate(http_server_duration_milliseconds_sum{{service_name="{service}"}}[{self.rate_window}]) / rate(http_server_duration_milliseconds_count{{service_name="{service}"}}[{self.rate_window}])'
        result = await self.query_prometheus(query)
        if result and len(result) > 0:
            value = result[0]['value'][1]
            if value != 'NaN':
                return float(value)
        
        # Fallback to http_server_request_duration_seconds (convert to ms)
        query = f'rate(http_server_request_duration_seconds_sum{{service_name="{service}"}}[{self.rate_window}]) / rate(http_server_request_duration_seconds_count{{service_name="{service}"}}[{self.rate_window}]) * 1000'
        result = await self.query_prometheus(query)
        if result and len(result) > 0:
            value = result[0]['value'][1]
            if value != 'NaN':
                return float(value)
        
        # Fallback to RPC metrics
        query = f'rate(rpc_server_duration_milliseconds_sum{{service_name="{service}"}}[{self.rate_window}]) / rate(rpc_server_duration_milliseconds_count{{service_name="{service}"}}[{self.rate_window}])'
        result = await self.query_prometheus(query)
        if result and len(result) > 0:
            value = result[0]['value'][1]
            if value != 'NaN':
                return float(value)
        
        return 0.0
        
    async def collect_service_metrics(self, service: str) -> ServiceMetrics:
        """Collect comprehensive metrics for a single service"""
        timestamp = datetime.utcnow().isoformat() + "Z"
        
        # Collect all metrics concurrently
        tasks = [
            self.get_service_rps(service),
            self.get_service_cpu(service),
            self.get_service_memory(service),
            self.get_service_latency(service, "0.50"),
            self.get_service_latency(service, "0.95"),
            self.get_service_latency(service, "0.99"),
            self.get_latency_mean(service),
            self.get_service_error_rate(service),
            self.get_service_connections(service),
            self.get_service_queue_depth(service),
            self.get_service_response_size(service),
            self.get_request_size(service),
            self.get_service_disk_read(service),
            self.get_service_disk_write(service),
            self.get_service_network_receive(service),
            self.get_service_network_transmit(service),
            self.get_replica_count(service),
            self.get_gc_collections(service),
            self.get_gc_pause_time(service),
            self.get_thread_count(service),
            self.get_heap_usage(service)
        ]
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Handle any exceptions and provide defaults
        safe_results = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                # Only log warnings for critical metrics
                if i < 8:  # Core metrics
                    logger.debug(f"Error collecting metric {i} for {service}: {result}")
                safe_results.append(0.0 if i not in [8, 9, 16, 19] else 0)
            else:
                safe_results.append(result)
        
        # Extract values
        rps = safe_results[0]
        cpu_percent = safe_results[1]
        memory_mb = safe_results[2]
        latency_p50 = safe_results[3]
        latency_p95 = safe_results[4]
        latency_p99 = safe_results[5]
        latency_mean = safe_results[6]
        error_rate = safe_results[7]
        active_connections = safe_results[8]
        queue_depth = safe_results[9]
        response_size_kb = safe_results[10]
        request_size_kb = safe_results[11]
        disk_read = safe_results[12]
        disk_write = safe_results[13]
        network_receive = safe_results[14]
        network_transmit = safe_results[15]
        replica_count = safe_results[16]
        gc_collections = safe_results[17]
        gc_pause = safe_results[18]
        thread_count = safe_results[19]
        heap_usage = safe_results[20]
        
        # Calculate derived metrics
        memory_limit = 500.0  # Assume 500MB limit, adjust based on service
        memory_utilization = (memory_mb / memory_limit * 100) if memory_limit > 0 else 0.0
        success_rate = 100.0 - error_rate
        disk_io_total = disk_read + disk_write
        network_io_total = network_receive + network_transmit
        requests_per_conn = (rps / active_connections) if active_connections > 0 else 0.0
        avg_response_time = latency_mean if latency_mean > 0 else latency_p50
        throughput = (rps * response_size_kb) / 1024  # MB/sec
        
        # Resource efficiency score (requests per unit of resource)
        resource_efficiency = 0.0
        if cpu_percent > 0 and memory_mb > 0:
            resource_efficiency = rps / (cpu_percent + memory_utilization / 10)
        
        return ServiceMetrics(
            timestamp=timestamp,
            service=service,
            # Performance Metrics
            rps=rps,
            latency_p50_ms=latency_p50,
            latency_p95_ms=latency_p95,
            latency_p99_ms=latency_p99,
            latency_mean_ms=latency_mean,
            error_rate=error_rate,
            success_rate=success_rate,
            # Resource Utilization
            cpu_percent=cpu_percent,
            memory_mb=memory_mb,
            memory_utilization_percent=memory_utilization,
            disk_read_mb_per_sec=disk_read,
            disk_write_mb_per_sec=disk_write,
            disk_io_mb_per_sec=disk_io_total,
            network_receive_mb_per_sec=network_receive,
            network_transmit_mb_per_sec=network_transmit,
            network_io_mb_per_sec=network_io_total,
            # Application Metrics
            active_connections=active_connections,
            queue_depth=queue_depth,
            response_size_kb=response_size_kb,
            request_size_kb=request_size_kb,
            thread_count=thread_count,
            heap_usage_mb=heap_usage,
            gc_collections_per_sec=gc_collections,
            gc_pause_time_ms=gc_pause,
            # Scaling Context
            replica_count=replica_count,
            target_cpu_utilization=70.0,
            target_memory_utilization=70.0,
            # Derived Metrics
            requests_per_connection=requests_per_conn,
            avg_response_time_ms=avg_response_time,
            throughput_mb_per_sec=throughput,
            resource_efficiency_score=resource_efficiency
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