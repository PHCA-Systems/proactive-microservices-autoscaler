#!/usr/bin/env python3
"""
Experiment Run Configuration
"""

from dataclasses import dataclass

SLO_THRESHOLD_MS = 36.0
NAMESPACE = "sock-shop"
POLL_INTERVAL_S = 30

MONITORED_SERVICES = [
    "front-end", "carts", "orders", "catalogue",
    "user", "payment", "shipping"
]

@dataclass
class ExperimentRun:
    condition: str    # "proactive" or "reactive"
    pattern:   str    # "constant", "step", "spike", "ramp"
    run_id:    int    # 1-based

# Repetitions per pattern per condition
REPETITIONS = {
    "constant": 2,
    "step":     5,
    "spike":    5,
    "ramp":     5,
}

# Total: (2+5+5+5) × 2 conditions = 34 runs
# Duration per run: 12 min load + 3 min settle = 15 min
# Total experiment time: 34 × 15 = ~8.5 hours

def generate_run_schedule() -> list[ExperimentRun]:
    """
    Alternates A/B per pattern to control for cluster drift.
    Order: proactive first, then reactive, for each pattern group.
    """
    schedule = []
    for pattern, reps in REPETITIONS.items():
        for i in range(1, reps + 1):
            schedule.append(ExperimentRun("proactive", pattern, i))
            schedule.append(ExperimentRun("reactive",  pattern, i))
    return schedule
