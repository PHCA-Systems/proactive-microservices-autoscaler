#!/usr/bin/env python3
"""
Feature Vector Builder
Builds ML-ready feature vectors from raw metrics
"""

from typing import Dict, Optional
from collections import defaultdict


class FeatureBuilder:
    def __init__(self):
        self.previous_metrics: Dict[str, dict] = {}
        
    def compute_deltas(
        self,
        current: dict,
        previous: Optional[dict]
    ) -> tuple:
        """Compute delta features."""
        if previous is None:
            return 0.0, 0.0, 0.0
        
        return (
            current["request_rate_rps"] - previous["request_rate_rps"],
            current["p95_latency_ms"] - previous["p95_latency_ms"],
            current["cpu_usage_pct"] - previous["cpu_usage_pct"],
        )
    
    def build_feature_vector(
        self,
        service: str,
        metrics: dict,
        timestamp: str
    ) -> dict:
        """
        Build a complete feature vector for ML inference.
        
        Returns:
            dict: Feature vector with all required fields
        """
        # Get previous metrics for this service
        prev = self.previous_metrics.get(service)
        
        # Compute deltas
        delta_rps, delta_p95, delta_cpu = self.compute_deltas(metrics, prev)
        
        # Build feature vector
        feature_vector = {
            "timestamp": timestamp,
            "service": service,
            "features": {
                "request_rate_rps": round(metrics["request_rate_rps"], 6),
                "error_rate_pct": round(metrics["error_rate_pct"], 6),
                "p50_latency_ms": round(metrics["p50_latency_ms"], 3),
                "p95_latency_ms": round(metrics["p95_latency_ms"], 3),
                "p99_latency_ms": round(metrics["p99_latency_ms"], 3),
                "cpu_usage_pct": round(metrics["cpu_usage_pct"], 6),
                "memory_usage_mb": round(metrics["memory_usage_mb"], 3),
                "delta_rps": round(delta_rps, 6),
                "delta_p95_latency_ms": round(delta_p95, 3),
                "delta_cpu_usage_pct": round(delta_cpu, 6),
            }
        }
        
        # Update previous metrics
        self.previous_metrics[service] = metrics.copy()
        
        return feature_vector
    
    def build_csv_row(
        self,
        service: str,
        metrics: dict,
        timestamp: str
    ) -> dict:
        """
        Build a CSV row for development mode (model retraining).
        
        Returns:
            dict: CSV row with all fields
        """
        feature_vector = self.build_feature_vector(service, metrics, timestamp)
        
        # Flatten for CSV
        row = {
            "timestamp": feature_vector["timestamp"],
            "service": feature_vector["service"],
        }
        row.update(feature_vector["features"])
        
        # Add placeholder for sla_violated (to be filled later)
        row["sla_violated"] = 0
        
        return row
