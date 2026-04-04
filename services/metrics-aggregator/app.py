#!/usr/bin/env python3
"""
Metrics Aggregator Service
Main application that polls Prometheus and publishes to Kafka or CSV
"""

import os
import sys
import time
import csv
from datetime import datetime, timezone
from pathlib import Path

from metrics_collector import MetricsCollector
from feature_builder import FeatureBuilder
from kafka_producer import MetricsKafkaProducer


# Configuration from environment
MODE = os.getenv("MODE", "production")
KAFKA_BOOTSTRAP_SERVERS = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "kafka:29092")
PROMETHEUS_URL = os.getenv("PROMETHEUS_URL", "http://prometheus:9090")
POLL_INTERVAL_SEC = int(os.getenv("POLL_INTERVAL_SEC", "30"))
OUTPUT_DIR = os.getenv("OUTPUT_DIR", "/output")

CSV_COLUMNS = [
    "timestamp", "service", "request_rate_rps", "error_rate_pct",
    "p50_latency_ms", "p95_latency_ms", "p99_latency_ms",
    "cpu_usage_pct", "memory_usage_mb", "delta_rps",
    "delta_p95_latency_ms", "delta_cpu_usage_pct", "sla_violated"
]


def setup_csv_writer(output_path: str):
    """Setup CSV writer for development mode."""
    file_exists = os.path.isfile(output_path)
    csv_file = open(output_path, "a", newline="", encoding="utf-8")
    writer = csv.DictWriter(csv_file, fieldnames=CSV_COLUMNS)
    
    if not file_exists:
        writer.writeheader()
        csv_file.flush()
    
    return csv_file, writer


def run_production_mode():
    """Run in production mode: Kafka publishing."""
    print("=" * 80)
    print("METRICS AGGREGATOR SERVICE - PRODUCTION MODE")
    print("=" * 80)
    print(f"Prometheus URL: {PROMETHEUS_URL}")
    print(f"Kafka Servers: {KAFKA_BOOTSTRAP_SERVERS}")
    print(f"Poll Interval: {POLL_INTERVAL_SEC} seconds")
    print("=" * 80)
    
    # Initialize components
    collector = MetricsCollector(PROMETHEUS_URL)
    builder = FeatureBuilder()
    
    # Wait for Kafka to be ready
    print("[INFO] Waiting 10 seconds for Kafka to be ready...")
    time.sleep(10)
    
    producer = MetricsKafkaProducer(KAFKA_BOOTSTRAP_SERVERS, topic="metrics")
    
    poll_count = 0
    
    try:
        while True:
            poll_start = time.time()
            timestamp = datetime.now(timezone.utc).isoformat()
            
            print(f"\n[POLL {poll_count}] {timestamp}")
            
            # Collect metrics from Prometheus
            metrics_snapshot = collector.collect_metrics()
            
            if not metrics_snapshot:
                print("[WARN] No metrics collected from Prometheus")
            else:
                print(f"[INFO] Collected metrics for {len(metrics_snapshot)} services")
            
            # Build and publish feature vectors
            published_count = 0
            for service, metrics in metrics_snapshot.items():
                feature_vector = builder.build_feature_vector(service, metrics, timestamp)
                
                # Publish to Kafka
                if producer.publish(feature_vector):
                    published_count += 1
                else:
                    print(f"[ERROR] Failed to publish metrics for service: {service}")
            
            print(f"[INFO] Published {published_count}/{len(metrics_snapshot)} feature vectors to Kafka")
            
            # Flush producer
            producer.flush()
            
            poll_count += 1
            
            # Sleep until next poll
            elapsed = time.time() - poll_start
            sleep_time = max(0, POLL_INTERVAL_SEC - elapsed)
            if sleep_time > 0:
                time.sleep(sleep_time)
    
    except KeyboardInterrupt:
        print("\n[INFO] Shutting down gracefully...")
    finally:
        producer.close()
        print("[INFO] Metrics aggregator stopped")


def run_development_mode():
    """Run in development mode: CSV writing."""
    print("=" * 80)
    print("METRICS AGGREGATOR SERVICE - DEVELOPMENT MODE")
    print("=" * 80)
    print(f"Prometheus URL: {PROMETHEUS_URL}")
    print(f"Poll Interval: {POLL_INTERVAL_SEC} seconds")
    print(f"Output Directory: {OUTPUT_DIR}")
    print("=" * 80)
    
    # Initialize components
    collector = MetricsCollector(PROMETHEUS_URL)
    builder = FeatureBuilder()
    
    # Setup CSV output
    output_path = os.path.join(OUTPUT_DIR, "sockshop_metrics.csv")
    csv_file, writer = setup_csv_writer(output_path)
    
    print(f"[INFO] Writing metrics to {output_path}")
    
    poll_count = 0
    
    try:
        while True:
            poll_start = time.time()
            timestamp = datetime.now(timezone.utc).isoformat()
            
            print(f"\n[POLL {poll_count}] {timestamp}")
            
            # Collect metrics from Prometheus
            metrics_snapshot = collector.collect_metrics()
            
            if not metrics_snapshot:
                print("[WARN] No metrics collected from Prometheus")
            else:
                print(f"[INFO] Collected metrics for {len(metrics_snapshot)} services")
            
            # Build and write CSV rows
            for service, metrics in metrics_snapshot.items():
                csv_row = builder.build_csv_row(service, metrics, timestamp)
                writer.writerow(csv_row)
            
            csv_file.flush()
            print(f"[INFO] Wrote {len(metrics_snapshot)} rows to CSV")
            
            poll_count += 1
            
            # Sleep until next poll
            elapsed = time.time() - poll_start
            sleep_time = max(0, POLL_INTERVAL_SEC - elapsed)
            if sleep_time > 0:
                time.sleep(sleep_time)
    
    except KeyboardInterrupt:
        print("\n[INFO] Shutting down gracefully...")
    finally:
        csv_file.close()
        print(f"[INFO] Metrics written to {output_path}")


def main():
    """Main entry point."""
    print(f"\n[INFO] Starting Metrics Aggregator Service")
    print(f"[INFO] Mode: {MODE}")
    
    # Wait for Prometheus to be ready
    print("[INFO] Waiting 15 seconds for Prometheus to be ready...")
    time.sleep(15)
    
    if MODE.lower() == "production":
        run_production_mode()
    elif MODE.lower() == "development":
        run_development_mode()
    else:
        print(f"[ERROR] Invalid MODE: {MODE}. Must be 'production' or 'development'")
        sys.exit(1)


if __name__ == "__main__":
    main()
