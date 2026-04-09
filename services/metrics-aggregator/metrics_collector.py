#!/usr/bin/env python3
"""
Prometheus Metrics Collector
Polls Prometheus and extracts per-service metrics
"""

import requests
from typing import Dict, List, Optional


class MetricsCollector:
    def __init__(self, prometheus_url: str):
        self.prometheus_url = prometheus_url.rstrip("/")
        self.default_services = [
            "carts", "catalogue", "front-end", "orders",
            "payment", "shipping", "user"
        ]

    def query(self, promql: str) -> List[dict]:
        """Run an instant PromQL query and return the result vector."""
        try:
            resp = requests.get(
                f"{self.prometheus_url}/api/v1/query",
                params={"query": promql},
                timeout=10,
            )
            resp.raise_for_status()
            data = resp.json()
            if data.get("status") == "success":
                return data["data"]["result"]
        except Exception as exc:
            print(f"[WARN] Prometheus query failed ({promql!r}): {exc}")
        return []

    def get_service_name(self, metric: dict) -> str:
        """Extract service name from metric labels."""
        if "service" in metric:
            return metric["service"]
        
        if "job" in metric:
            job = metric["job"]
            job_to_service = {"cart": "carts", "frontend": "front-end"}
            return job_to_service.get(job, job)
        
        if "instance" in metric:
            instance = metric["instance"]
            if ":" in instance:
                instance = instance.split(":")[0]
            return instance
        
        return "unknown"

    def float_value(self, result_item: dict, default: float = 0.0) -> float:
        """Extract float value from Prometheus result."""
        try:
            return float(result_item["value"][1])
        except (KeyError, IndexError, ValueError, TypeError):
            return default

    def collect_metrics(self) -> Dict[str, dict]:
        """
        Collect all metrics from Prometheus and return per-service dict.
        """
        # Request rate (RPS)
        rps_results = self.query(
            'sum(rate(request_duration_seconds_count[1m])) by (job, service, instance)'
        )
        rps_by_service: Dict[str, float] = {}
        for r in rps_results:
            svc = self.get_service_name(r.get("metric", {}))
            rps_by_service[svc] = rps_by_service.get(svc, 0.0) + self.float_value(r)

        # Error rate
        err_num_results = self.query(
            'sum(rate(request_duration_seconds_count{status_code=~"5.."}[1m])) by (job, service, instance)'
        )
        err_num_by_service: Dict[str, float] = {}
        for r in err_num_results:
            svc = self.get_service_name(r.get("metric", {}))
            err_num_by_service[svc] = err_num_by_service.get(svc, 0.0) + self.float_value(r)

        # Latency percentiles
        p50_results = self.query(
            'histogram_quantile(0.50, sum(rate(request_duration_seconds_bucket[1m])) by (le, job, service, instance))'
        )
        p50_by_service: Dict[str, List[float]] = {}
        for r in p50_results:
            svc = self.get_service_name(r.get("metric", {}))
            if svc not in p50_by_service:
                p50_by_service[svc] = []
            p50_by_service[svc].append(self.float_value(r) * 1000.0)

        p95_results = self.query(
            'histogram_quantile(0.95, sum(rate(request_duration_seconds_bucket[1m])) by (le, job, service, instance))'
        )
        p95_by_service: Dict[str, List[float]] = {}
        for r in p95_results:
            svc = self.get_service_name(r.get("metric", {}))
            if svc not in p95_by_service:
                p95_by_service[svc] = []
            p95_by_service[svc].append(self.float_value(r) * 1000.0)

        p99_results = self.query(
            'histogram_quantile(0.99, sum(rate(request_duration_seconds_bucket[1m])) by (le, job, service, instance))'
        )
        p99_by_service: Dict[str, List[float]] = {}
        for r in p99_results:
            svc = self.get_service_name(r.get("metric", {}))
            if svc not in p99_by_service:
                p99_by_service[svc] = []
            p99_by_service[svc].append(self.float_value(r) * 1000.0)

        # Average latencies
        p50_avg = {svc: sum(vals) / len(vals) if vals else 0.0 for svc, vals in p50_by_service.items()}
        p95_avg = {svc: sum(vals) / len(vals) if vals else 0.0 for svc, vals in p95_by_service.items()}
        p99_avg = {svc: sum(vals) / len(vals) if vals else 0.0 for svc, vals in p99_by_service.items()}

        # CPU usage
        cpu_results = self.query('rate(process_cpu_seconds_total[1m])')
        cpu_by_service: Dict[str, float] = {}
        for r in cpu_results:
            svc = self.get_service_name(r.get("metric", {}))
            cpu_by_service[svc] = cpu_by_service.get(svc, 0.0) + self.float_value(r) * 100.0

        # Memory usage
        mem_results = self.query('process_resident_memory_bytes')
        mem_by_service: Dict[str, float] = {}
        for r in mem_results:
            svc = self.get_service_name(r.get("metric", {}))
            mem_by_service[svc] = mem_by_service.get(svc, 0.0) + self.float_value(r) / (1024 ** 2)

        # Assemble per-service dict — restrict to known Sock Shop services only
        all_services = set(self.default_services)

        metrics: Dict[str, dict] = {}
        for svc in all_services:
            rps = rps_by_service.get(svc, 0.0)
            err_num = err_num_by_service.get(svc, 0.0)
            error_rate = (err_num / rps * 100.0) if rps > 0 else 0.0
            
            metrics[svc] = {
                "request_rate_rps": rps,
                "error_rate_pct": error_rate,
                "p50_latency_ms": p50_avg.get(svc, 0.0),
                "p95_latency_ms": p95_avg.get(svc, 0.0),
                "p99_latency_ms": p99_avg.get(svc, 0.0),
                "cpu_usage_pct": cpu_by_service.get(svc, 0.0),
                "memory_usage_mb": mem_by_service.get(svc, 0.0),
            }
        
        return metrics
