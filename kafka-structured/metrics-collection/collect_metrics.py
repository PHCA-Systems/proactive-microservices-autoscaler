#!/usr/bin/env python3
"""
Sock Shop Prometheus Metrics Collector
======================================
Polls Prometheus every 30 seconds and writes labelled training data to
sockshop_metrics.csv.  Rows are held in a buffer until their 60-second
lookahead window has closed, then flushed with the correct sla_violated label.

Usage:
    python collect_metrics.py [--prometheus URL] [--duration MINUTES] [--output FILE]
"""

import argparse
import csv
import os
import time
from collections import defaultdict
from datetime import datetime, timezone

import requests

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
POLL_INTERVAL_SEC = 30          # seconds between polls
LOOKAHEAD_WINDOWS = 2           # number of future polls used for labelling
P95_SLA_THRESHOLD_MS = 9.86     # ms – SLA violation threshold

CSV_COLUMNS = [
    "timestamp",
    "service",
    "request_rate_rps",
    "error_rate_pct",
    "p50_latency_ms",
    "p95_latency_ms",
    "p99_latency_ms",
    "cpu_usage_pct",
    "memory_usage_mb",
    "delta_rps",
    "delta_p95_latency_ms",
    "delta_cpu_usage_pct",
    "sla_violated",
]

# Known Sock Shop services – used as a fallback if Prometheus returns no data
DEFAULT_SERVICES = [
    "carts",
    "catalogue",
    "front-end",
    "orders",
    "payment",
    "queue-master",
    "shipping",
    "user",
]


# ---------------------------------------------------------------------------
# Prometheus helpers
# ---------------------------------------------------------------------------

def query(prom_url: str, promql: str) -> list:
    """Run an instant PromQL query and return the result vector."""
    try:
        resp = requests.get(
            f"{prom_url}/api/v1/query",
            params={"query": promql},
            timeout=10,
        )
        resp.raise_for_status()
        data = resp.json()
        if data.get("status") == "success":
            return data["data"]["result"]
    except Exception as exc:  # noqa: BLE001
        print(f"[WARN] Prometheus query failed ({promql!r}): {exc}")
    return []


def label_value(result_item: dict, label: str, default: str = "unknown") -> str:
    return result_item.get("metric", {}).get(label, default)


def float_value(result_item: dict, default: float = 0.0) -> float:
    try:
        return float(result_item["value"][1])
    except (KeyError, IndexError, ValueError, TypeError):
        return default


def get_service_name(metric: dict) -> str:
    """
    Extract service name from metric labels.
    Sock Shop uses different label conventions:
    - 'service' label for some metrics (front-end, carts)
    - 'job' label for others (catalogue, user, payment, cart, orders, shipping, queue-master)
    - 'instance' as fallback
    """
    # Try 'service' label first (used by edge-router/front-end)
    if "service" in metric:
        return metric["service"]
    
    # Try 'job' label and normalize known service names
    if "job" in metric:
        job = metric["job"]
        # Normalize job names to service names
        job_to_service = {
            "cart": "carts",
            "frontend": "front-end",
        }
        return job_to_service.get(job, job)
    
    # Fallback to instance
    if "instance" in metric:
        instance = metric["instance"]
        # Clean up instance names (remove port numbers, etc.)
        if ":" in instance:
            instance = instance.split(":")[0]
        return instance
    
    return "unknown"


# ---------------------------------------------------------------------------
# Metric collection
# ---------------------------------------------------------------------------

def collect_metrics(prom_url: str) -> dict[str, dict]:
    """
    Return a dict keyed by service name with all raw metric values.
    Missing values default to 0.0.
    """

    # ---- request rate (rps) -----------------------------------------------
    # Group by job and service labels to capture all services
    rps_results = query(
        prom_url,
        'sum(rate(request_duration_seconds_count[1m])) by (job, service, instance)',
    )
    rps_by_service: dict[str, float] = {}
    for r in rps_results:
        svc = get_service_name(r.get("metric", {}))
        rps_by_service[svc] = rps_by_service.get(svc, 0.0) + float_value(r)

    # ---- error rate -----------------------------------------------------------
    err_num_results = query(
        prom_url,
        'sum(rate(request_duration_seconds_count{status_code=~"5.."}[1m])) by (job, service, instance)',
    )
    err_num_by_service: dict[str, float] = {}
    for r in err_num_results:
        svc = get_service_name(r.get("metric", {}))
        err_num_by_service[svc] = err_num_by_service.get(svc, 0.0) + float_value(r)

    # ---- latency percentiles -------------------------------------------------
    # Group by job and service to get per-service histograms
    p50_results = query(
        prom_url,
        'histogram_quantile(0.50, sum(rate(request_duration_seconds_bucket[1m])) by (le, job, service, instance))',
    )
    p50_by_service: dict[str, list[float]] = {}
    for r in p50_results:
        svc = get_service_name(r.get("metric", {}))
        if svc not in p50_by_service:
            p50_by_service[svc] = []
        p50_by_service[svc].append(float_value(r) * 1000.0)  # s → ms

    p95_results = query(
        prom_url,
        'histogram_quantile(0.95, sum(rate(request_duration_seconds_bucket[1m])) by (le, job, service, instance))',
    )
    p95_by_service: dict[str, list[float]] = {}
    for r in p95_results:
        svc = get_service_name(r.get("metric", {}))
        if svc not in p95_by_service:
            p95_by_service[svc] = []
        p95_by_service[svc].append(float_value(r) * 1000.0)

    p99_results = query(
        prom_url,
        'histogram_quantile(0.99, sum(rate(request_duration_seconds_bucket[1m])) by (le, job, service, instance))',
    )
    p99_by_service: dict[str, list[float]] = {}
    for r in p99_results:
        svc = get_service_name(r.get("metric", {}))
        if svc not in p99_by_service:
            p99_by_service[svc] = []
        p99_by_service[svc].append(float_value(r) * 1000.0)

    # Average latencies if multiple values per service
    p50_avg = {svc: sum(vals) / len(vals) if vals else 0.0 for svc, vals in p50_by_service.items()}
    p95_avg = {svc: sum(vals) / len(vals) if vals else 0.0 for svc, vals in p95_by_service.items()}
    p99_avg = {svc: sum(vals) / len(vals) if vals else 0.0 for svc, vals in p99_by_service.items()}

    # ---- CPU usage (%) -------------------------------------------------------
    # Use process-level CPU metrics (rate of process_cpu_seconds_total)
    cpu_results = query(
        prom_url,
        'rate(process_cpu_seconds_total[1m])',
    )
    cpu_by_service: dict[str, float] = {}
    for r in cpu_results:
        svc = get_service_name(r.get("metric", {}))
        # rate gives cores/sec, multiply by 100 to get percentage
        cpu_by_service[svc] = cpu_by_service.get(svc, 0.0) + float_value(r) * 100.0

    # ---- Memory usage (MB) ---------------------------------------------------
    # Use process-level memory metrics
    mem_results = query(
        prom_url,
        'process_resident_memory_bytes',
    )
    mem_by_service: dict[str, float] = {}
    for r in mem_results:
        svc = get_service_name(r.get("metric", {}))
        mem_by_service[svc] = mem_by_service.get(svc, 0.0) + float_value(r) / (1024 ** 2)  # bytes → MB

    # ---- Assemble per-service dict ------------------------------------------
    all_services = (
        set(rps_by_service)
        | set(p95_avg)
        | set(cpu_by_service)
        | set(mem_by_service)
    )
    if not all_services:
        all_services = set(DEFAULT_SERVICES)

    metrics: dict[str, dict] = {}
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


def compute_deltas(
    current: dict[str, float],
    previous: dict[str, float] | None,
) -> tuple[float, float, float]:
    """Return (delta_rps, delta_p95_latency_ms, delta_cpu_usage_pct)."""
    if previous is None:
        return 0.0, 0.0, 0.0
    return (
        current["request_rate_rps"] - previous["request_rate_rps"],
        current["p95_latency_ms"] - previous["p95_latency_ms"],
        current["cpu_usage_pct"] - previous["cpu_usage_pct"],
    )


def check_constant_latency_pattern(service: str, latency_history: list[tuple[float, float, float]], min_samples: int = 5) -> None:
    """
    Check if a service shows constant latency values and log an informational message.
    
    This is expected behavior for very fast services (<5ms) due to Prometheus histogram
    bucket granularity limitations. When 99%+ of requests complete in the first bucket
    (0-5ms), histogram_quantile() interpolation produces constant values.
    
    Args:
        service: Service name
        latency_history: List of (p50, p95, p99) tuples
        min_samples: Minimum number of samples before checking
    """
    if len(latency_history) < min_samples:
        return
    
    # Check if all recent samples have the same latency triplet
    recent = latency_history[-min_samples:]
    unique_triplets = set(recent)
    
    if len(unique_triplets) == 1:
        p50, p95, p99 = recent[0]
        # Check for the specific pattern caused by histogram interpolation
        if abs(p50 - 2.5) < 0.01 and abs(p95 - 4.75) < 0.01 and abs(p99 - 4.95) < 0.01:
            print(f"[INFO] {service}: Constant latency pattern detected (p50={p50:.2f}ms, p95={p95:.2f}ms, p99={p99:.2f}ms)")
            print(f"       This is EXPECTED for very fast services (<5ms) due to Prometheus histogram bucket granularity.")
            print(f"       See output/CONSTANT_LATENCY_EXPLANATION.txt for details.")


# ---------------------------------------------------------------------------
# Main loop
# ---------------------------------------------------------------------------

def run(prom_url: str, duration_min: float, output_path: str) -> None:
    end_time = time.monotonic() + duration_min * 60.0

    # Buffer: list of (timestamp_str, service, row_dict)
    buffer: list[tuple[str, str, dict]] = []

    # per-service history of p95 latency values  [oldest … newest]
    p95_history: dict[str, list[float]] = defaultdict(list)
    
    # per-service history of latency triplets for validation
    latency_triplet_history: dict[str, list[tuple[float, float, float]]] = defaultdict(list)
    
    # track if we've already logged constant latency warning for each service
    constant_latency_logged: dict[str, bool] = defaultdict(bool)

    # previous poll snapshot for delta calculation
    prev_snap: dict[str, dict] | None = None

    # ---- CSV setup -----------------------------------------------------------
    file_exists = os.path.isfile(output_path)
    csv_file = open(output_path, "a", newline="", encoding="utf-8")  # noqa: WPS515
    writer = csv.DictWriter(csv_file, fieldnames=CSV_COLUMNS)
    if not file_exists:
        writer.writeheader()
        csv_file.flush()

    print(f"[INFO] Writing metrics to {output_path}")
    print(f"[INFO] Running for {duration_min} minute(s) …")

    poll_index = 0

    try:
        while time.monotonic() < end_time:
            poll_start = time.monotonic()
            now_utc = datetime.now(timezone.utc).isoformat()

            print(f"[POLL {poll_index}] {now_utc}")
            current_snap = collect_metrics(prom_url)

            for svc, vals in current_snap.items():
                d_rps, d_p95, d_cpu = compute_deltas(vals, (prev_snap or {}).get(svc))

                row = {
                    "timestamp": now_utc,
                    "service": svc,
                    "request_rate_rps": round(vals["request_rate_rps"], 6),
                    "error_rate_pct": round(vals["error_rate_pct"], 6),
                    "p50_latency_ms": round(vals["p50_latency_ms"], 3),
                    "p95_latency_ms": round(vals["p95_latency_ms"], 3),
                    "p99_latency_ms": round(vals["p99_latency_ms"], 3),
                    "cpu_usage_pct": round(vals["cpu_usage_pct"], 6),
                    "memory_usage_mb": round(vals["memory_usage_mb"], 3),
                    "delta_rps": round(d_rps, 6),
                    "delta_p95_latency_ms": round(d_p95, 3),
                    "delta_cpu_usage_pct": round(d_cpu, 6),
                    # sla_violated filled in once lookahead closes
                }
                buffer.append((now_utc, svc, row, poll_index))
                p95_history[svc].append(vals["p95_latency_ms"])
                
                # Track latency triplets for validation
                triplet = (vals["p50_latency_ms"], vals["p95_latency_ms"], vals["p99_latency_ms"])
                latency_triplet_history[svc].append(triplet)
                
                # Check for constant latency pattern (only log once per service)
                if not constant_latency_logged[svc] and len(latency_triplet_history[svc]) >= 5:
                    check_constant_latency_pattern(svc, latency_triplet_history[svc])
                    # Check if warning was triggered (all 5 samples are the same)
                    if len(set(latency_triplet_history[svc][-5:])) == 1:
                        constant_latency_logged[svc] = True

            prev_snap = current_snap
            poll_index += 1

            # ---- Flush rows whose lookahead window has closed ----------------
            # A row collected at poll N can be labelled at poll N + LOOKAHEAD_WINDOWS.
            ready_cutoff = poll_index - LOOKAHEAD_WINDOWS
            remaining_buffer = []
            for entry in buffer:
                ts, svc, row, row_poll = entry
                if row_poll <= ready_cutoff:
                    # Look at the next LOOKAHEAD_WINDOWS polls in p95_history
                    history = p95_history[svc]
                    start_idx = row_poll + 1
                    end_idx = row_poll + 1 + LOOKAHEAD_WINDOWS
                    future_p95 = history[start_idx:end_idx]
                    violated = any(v > P95_SLA_THRESHOLD_MS for v in future_p95)
                    row["sla_violated"] = int(violated)
                    writer.writerow(row)
                else:
                    remaining_buffer.append(entry)
            buffer = remaining_buffer
            csv_file.flush()

            # ---- Sleep until next poll ---------------------------------------
            elapsed = time.monotonic() - poll_start
            sleep_for = max(0.0, POLL_INTERVAL_SEC - elapsed)
            if sleep_for > 0:
                time.sleep(sleep_for)

    except KeyboardInterrupt:
        print("\n[INFO] Interrupted by user.")

    finally:
        # Flush whatever remains in the buffer with best-effort labels
        print(f"[INFO] Flushing {len(buffer)} unlabelled row(s) from buffer …")
        for ts, svc, row, row_poll in buffer:
            history = p95_history[svc]
            start_idx = row_poll + 1
            end_idx = row_poll + 1 + LOOKAHEAD_WINDOWS
            future_p95 = history[start_idx:end_idx]
            if future_p95:
                violated = any(v > P95_SLA_THRESHOLD_MS for v in future_p95)
                row["sla_violated"] = int(violated)
            else:
                # Not enough future data – label as 0 (conservative)
                row["sla_violated"] = 0
            writer.writerow(row)
        csv_file.flush()
        csv_file.close()
        print(f"[INFO] Done. Data written to {output_path}")


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Collect Sock Shop metrics from Prometheus and label SLA violations.",
    )
    parser.add_argument(
        "--prometheus",
        default="http://localhost:9090",
        metavar="URL",
        help="Base URL of the Prometheus server (default: http://localhost:9090)",
    )
    parser.add_argument(
        "--duration",
        type=float,
        default=10.0,
        metavar="MINUTES",
        help="How long to run the collector in minutes (default: 10)",
    )
    parser.add_argument(
        "--output",
        default="sockshop_metrics.csv",
        metavar="FILE",
        help="Path to the output CSV file (default: sockshop_metrics.csv)",
    )
    args = parser.parse_args()

    run(
        prom_url=args.prometheus.rstrip("/"),
        duration_min=args.duration,
        output_path=args.output,
    )


if __name__ == "__main__":
    main()
