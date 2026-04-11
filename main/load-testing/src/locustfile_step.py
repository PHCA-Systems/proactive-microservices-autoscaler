"""
EuroSys'24 Step Load Pattern - Stochastic Load Generation
Based on EuroSys'24 Paper: "Erlang: Application-Aware Autoscaling for Cloud Microservices"

Step Load Pattern: Sudden traffic variations with bursts and drops
"""

import random
import time
from locust import HttpUser, task, constant, LoadTestShape

# Fixed Sock Shop catalogue data (standard demo items)
item_ids = [
    "a0eebc99-9c0b-4ef8-bb6d-6bb9bd380a11",
    "3395a43e-5d8d-4d79-ac8c-0d58e637d5e8", 
    "03fef6c8-7c4f-4f69-8a7d-6e48d4c1db8e",
    "d3588630-ad8e-49df-b6f8-5e4f3c0e5e2e",
    "510a0d7e-8e83-4193-b483-e27e9ddc34d8",
    "808a2de1-1aaa-4c25-a9b9-79a93b77c087",
    "819e1fbf-a459-4c89-9e03-9b5d1a5fc1b0",
    "zzz4f044-ec42-4f2b-a2d8-7e4b3f4a5c6d"
]

# Standard Sock Shop tags for realistic browsing
tags = ["red", "blue", "black", "white", "brown", "green", "gray", "purple"]

class SockShopUser(HttpUser):
    """Stochastic user behavior implementation following EuroSys'24 paper methodology."""
    
    wait_time = constant(2)  # Exact paper: action every ~2 seconds
    timeout = 2  # Exact paper: 2s client timeout (mimics user bouncing)
    host = "http://localhost:80"  # Sock Shop edge-router on port 80
    
    def on_start(self):
        """Initialize session - no login required for Sock Shop demo."""
        # Create a session ID for cart management
        self.session_id = f"session_{random.randint(1000, 9999)}"
        self.cart_items = []  # Track items in cart
        self.has_items_in_cart = False
        
        # Note: Sock Shop demo doesn't require authentication for basic operations
    
    # Weighted tasks (total weight = 117)
    @task(25)  # ~21.4% - Home page browsing
    def browse_home(self):
        self.client.get("/", name="browse_home")
    
    @task(20)  # ~17.1% - General catalogue browsing  
    def browse_catalogue(self):
        self.client.get("/catalogue", name="browse_catalogue")
    
    @task(20)  # ~17.1% - Category-based browsing
    def browse_category(self):
        tag = random.choice(tags)
        self.client.get(f"/category.html?tags={tag}", name="browse_category")
    
    @task(20)  # ~17.1% - Item detail viewing
    def view_item(self):
        item_id = random.choice(item_ids)
        self.client.get(f"/detail.html?id={item_id}", name="view_item")
    
    @task(10)  # ~8.5% - Add to cart
    def add_to_cart(self):
        """Add item to cart and track for realistic checkout behavior."""
        item_id = random.choice(item_ids)
        cart_data = {"id": item_id, "quantity": 1}
        
        # Add to cart and track items
        response = self.client.post("/cart", json=cart_data, name="add_to_cart")
        
        # Track items in cart for realistic checkout behavior
        if response.status_code == 200:
            self.cart_items.append(item_id)
            self.has_items_in_cart = True
    
    @task(8)  # ~6.8% - View cart contents
    def view_cart(self):
        self.client.get("/basket.html", name="view_cart")
    
    @task(4)  # ~3.4% - Checkout
    def checkout(self):
        """
        Unconditional checkout attempt following EuroSys'24 methodology.
        Checkout may fail naturally due to system constraints, not artificial logic.
        """
        # Always attempt checkout - use the customer orders page
        self.client.get("/customer-orders.html", name="checkout")

class StepLoad(LoadTestShape):
    """
    Step load pattern with sudden increases and decreases.
    EuroSys'24 Paper: Sudden traffic variations pattern.
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
