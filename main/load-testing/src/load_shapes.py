"""
Load Pattern Classes for EuroSys'24 Paper Reproduction
Custom LoadTestShape classes implementing the four paper patterns:

1. Constant Load: Steady-state user count
2. Step Load: Sudden increases/decreases  
3. Spike Load: Sharp bursts followed by quiet periods
4. Ramp Load: Gradual increase/decrease

All patterns maintain the stochastic user behavior from locustfile.py
"""

from locust import LoadTestShape
import time

class ConstantLoad(LoadTestShape):
    """
    Constant steady-state load pattern.
    Maintains fixed user count throughout test duration.
    """
    
    def __init__(self):
        super().__init__()
        self.user_count = 50  # Target constant user count
        self.spawn_rate = 5   # Users spawned per second
        self.test_duration = 600  # 10 minutes test duration
    
    def tick(self):
        run_time = self.get_run_time()
        
        if run_time < self.test_duration:
            return (self.user_count, self.spawn_rate)
        else:
            return None

class StepLoad(LoadTestShape):
    """
    Step load pattern with sudden increases and decreases.
    Simulates traffic bursts and drops.
    """
    
    def __init__(self):
        super().__init__()
        self.steps = [
            (0, 100, 10),    # (start_time, user_count, spawn_rate)
            (120, 200, 20),   # Step up at 2 minutes
            (240, 100, 10),   # Step down at 4 minutes  
            (360, 300, 30),   # Step up to peak at 6 minutes
            (480, 50, 5),     # Step down to minimum at 8 minutes
        ]
        self.test_duration = 600
    
    def tick(self):
        run_time = self.get_run_time()
        
        if run_time >= self.test_duration:
            return None
            
        # Find current step
        current_step = (50, 5)  # Default values
        for start_time, user_count, spawn_rate in self.steps:
            if run_time >= start_time:
                current_step = (user_count, spawn_rate)
            else:
                break
                
        return current_step

class SpikeLoad(LoadTestShape):
    """
    Spike load pattern with sharp bursts followed by quiet periods.
    Simulates flash crowd or viral traffic patterns.
    """
    
    def __init__(self):
        super().__init__()
        self.spikes = [
            (60, 30, 15),     # (spike_time, duration, peak_users)
            (180, 30, 50),    # Larger spike at 3 minutes
            (300, 30, 100),   # Major spike at 5 minutes
            (420, 30, 25),    # Smaller spike at 7 minutes
        ]
        self.base_users = 10
        self.base_spawn_rate = 2
        self.test_duration = 600
    
    def tick(self):
        run_time = self.get_run_time()
        
        if run_time >= self.test_duration:
            return None
            
        # Check if we're in a spike period
        for spike_time, duration, peak_users in self.spikes:
            if spike_time <= run_time < spike_time + duration:
                return (peak_users, 20)  # High spawn rate for spikes
        
        # Base load during non-spike periods
        return (self.base_users, self.base_spawn_rate)

class RampLoad(LoadTestShape):
    """
    Ramp load pattern with gradual increase and decrease.
    Simulates organic traffic growth and decline.
    """
    
    def __init__(self):
        super().__init__()
        self.ramp_up_duration = 300   # 5 minutes ramp up
        self.peak_duration = 120      # 2 minutes at peak
        self.ramp_down_duration = 180 # 3 minutes ramp down
        self.min_users = 10
        self.max_users = 150
        self.test_duration = 600
    
    def tick(self):
        run_time = self.get_run_time()
        
        if run_time >= self.test_duration:
            return None
            
        if run_time <= self.ramp_up_duration:
            # Ramp up phase
            progress = run_time / self.ramp_up_duration
            current_users = int(self.min_users + (self.max_users - self.min_users) * progress)
            spawn_rate = 10
        elif run_time <= self.ramp_up_duration + self.peak_duration:
            # Peak phase
            current_users = self.max_users
            spawn_rate = 5
        elif run_time <= self.ramp_up_duration + self.peak_duration + self.ramp_down_duration:
            # Ramp down phase
            ramp_down_start = self.ramp_up_duration + self.peak_duration
            progress = (run_time - ramp_down_start) / self.ramp_down_duration
            current_users = int(self.max_users - (self.max_users - self.min_users) * progress)
            spawn_rate = 8
        else:
            return None
            
        return (current_users, spawn_rate)
