"""
Mixed 4-hour load pattern for GKE replication of local dataset.
Cycles through all 4 patterns sequentially, repeating until duration is reached.
Each cycle: constant(20m) -> ramp(15m) -> spike(15m) -> step(15m) = 65 min per cycle
4 hours = ~3.7 cycles, giving a realistic mixed workload.

Duration controlled by LOCUST_RUN_TIME_MINUTES env var (default 240 = 4 hours).
"""

import os
import random
from locust import HttpUser, task, constant, LoadTestShape

item_ids = [
    "03fef6ac-1896-4ce8-bd69-b798f85c6e0b",
    "3395a43e-2d88-40de-b95f-e00e1502085b",
    "510a0d7e-8e83-4193-b483-e27e09ddc34d",
    "808a2de1-1aaa-4c25-a9b9-6612e8f29a38",
    "819e1fbf-8b7e-4f6d-811f-693534916a8b",
    "837ab141-399e-4c1f-9abc-bace40296bac",
    "a0a4f044-b040-410d-8ead-4de0446aec7e",
    "d3588630-ad8e-49df-bbd7-3167f7efb246",
]
tags = ["red", "blue", "black", "white", "brown", "green", "gray", "purple"]


class SockShopUser(HttpUser):
    wait_time = constant(2)
    timeout = 2

    def on_start(self):
        import base64
        self.cart_items = []
        credentials = base64.b64encode(b"user:password").decode()
        self.auth_header = {"Authorization": f"Basic {credentials}"}
        self.client.get("/login", headers=self.auth_header, name="login")

    @task(25)
    def browse_home(self):
        self.client.get("/", name="browse_home")

    @task(20)
    def browse_catalogue(self):
        self.client.get("/catalogue", name="browse_catalogue")

    @task(20)
    def browse_category(self):
        self.client.get(f"/category.html?tags={random.choice(tags)}", name="browse_category")

    @task(20)
    def view_item(self):
        self.client.get(f"/detail.html?id={random.choice(item_ids)}", name="view_item")

    @task(10)
    def add_to_cart(self):
        item_id = random.choice(item_ids)
        r = self.client.post("/cart", json={"id": item_id, "quantity": 1}, name="add_to_cart")
        if r.status_code == 200:
            self.cart_items.append(item_id)

    @task(8)
    def view_cart(self):
        self.client.get("/basket.html", name="view_cart")

    @task(4)
    def checkout(self):
        self.client.delete("/cart", name="clear_cart")
        self.client.post("/cart", json={"id": random.choice(item_ids), "quantity": 1}, name="add_for_checkout")
        self.client.post("/orders", headers=self.auth_header, name="checkout")


class MixedLoad(LoadTestShape):
    """
    Cycles through constant -> ramp -> spike -> step repeatedly.
    Segment durations (seconds):
      constant: 1200s (20 min)
      ramp:      900s (15 min)
      spike:     900s (15 min)
      step:      900s (15 min)
    One full cycle = 3900s (65 min)
    """

    SEGMENTS = [
        # (duration_sec, type)
        (1200, "constant"),
        (900,  "ramp"),
        (900,  "spike"),
        (900,  "step"),
    ]
    CYCLE_DURATION = sum(d for d, _ in SEGMENTS)

    def __init__(self):
        super().__init__()
        duration_minutes = int(os.environ.get('LOCUST_RUN_TIME_MINUTES', '240'))
        self.test_duration = duration_minutes * 60

        # Ramp params
        self.ramp_min, self.ramp_max = 10, 150

        # Spike params
        self.spike_base = 10

        # Step params
        self.step_levels = [100, 200, 100, 300, 50]

    def _segment_at(self, t):
        """Return (segment_type, time_within_segment) for global time t."""
        t_in_cycle = t % self.CYCLE_DURATION
        elapsed = 0
        for dur, seg_type in self.SEGMENTS:
            if t_in_cycle < elapsed + dur:
                return seg_type, t_in_cycle - elapsed
            elapsed += dur
        return self.SEGMENTS[-1][1], self.SEGMENTS[-1][0]

    def tick(self):
        run_time = self.get_run_time()
        if run_time >= self.test_duration:
            return None

        seg_type, t = self._segment_at(run_time)

        if seg_type == "constant":
            return (50, 5)

        elif seg_type == "ramp":
            dur = 900
            up   = int(dur * 0.5)
            peak = int(dur * 0.2)
            down = int(dur * 0.3)
            if t <= up:
                users = int(self.ramp_min + (self.ramp_max - self.ramp_min) * t / up)
                return (users, 10)
            elif t <= up + peak:
                return (self.ramp_max, 5)
            else:
                progress = (t - up - peak) / down
                users = int(self.ramp_max - (self.ramp_max - self.ramp_min) * progress)
                return (max(users, self.ramp_min), 8)

        elif seg_type == "spike":
            dur = 900
            interval = dur / 7
            spikes = [
                (int(interval * 1), 30, 15),
                (int(interval * 3), 30, 50),
                (int(interval * 5), 30, 100),
                (int(interval * 6.5), 30, 25),
            ]
            for spike_t, spike_dur, peak in spikes:
                if spike_t <= t < spike_t + spike_dur:
                    return (peak, 20)
            return (self.spike_base, 2)

        elif seg_type == "step":
            dur = 900
            interval = dur / 5
            steps = [
                (0,                  100, 10),
                (int(interval * 1),  200, 20),
                (int(interval * 2),  100, 10),
                (int(interval * 3),  300, 30),
                (int(interval * 4),   50,  5),
            ]
            current = (50, 5)
            for start, users, rate in steps:
                if t >= start:
                    current = (users, rate)
                else:
                    break
            return current

        return (50, 5)
