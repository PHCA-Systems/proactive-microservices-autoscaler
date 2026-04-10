"""
EuroSys'24 Step Load Pattern - Stochastic Load Generation
Based on EuroSys'24 Paper: "Erlang: Application-Aware Autoscaling for Cloud Microservices"

Step Load Pattern: Sudden traffic variations with bursts and drops
"""

import random
import time
from locust import HttpUser, task, constant, LoadTestShape

# Fixed Sock Shop catalogue data (valid IDs from running instance)
item_ids = [
    "03fef6ac-1896-4ce8-bd69-b798f85c6e0b",  # Holy
    "3395a43e-2d88-40de-b95f-e00e1502085b",  # Colourful
    "510a0d7e-8e83-4193-b483-e27e09ddc34d",  # SuperSport XL
    "808a2de1-1aaa-4c25-a9b9-6612e8f29a38",  # Classic
    "819e1fbf-8b7e-4f6d-811f-693534916a8b",  # Figueroa
    "837ab141-399e-4c1f-9abc-bace40296bac",  # YouTube.sock
    "a0a4f044-b040-410d-8ead-4de0446aec7e",  # Weave special
    "d3588630-ad8e-49df-bbd7-3167f7efb246"   # Nerd leg
]

# Standard Sock Shop tags for realistic browsing
tags = ["red", "blue", "black", "white", "brown", "green", "gray", "purple"]

class SockShopUser(HttpUser):
    """Stochastic user behavior implementation following EuroSys'24 paper methodology."""
    
    wait_time = constant(2)  # Exact paper: action every ~2 seconds
    timeout = 2  # Exact paper: 2s client timeout (mimics user bouncing)
    host = "http://localhost:80"  # Sock Shop edge-router on port 80
    
    def on_start(self):
        """
        Initialize session with Basic Authentication per official Sock Shop demo.
        Official load test uses: username='user', password='password'
        EuroSys'24 paper: Login once per user; session/cookies maintain cart state.
        """
        import base64
        
        # Initialize cart tracking
        self.cart_items = []
        self.has_items_in_cart = False
        
        # Use official Sock Shop demo credentials
        self.username = "user"
        self.password = "password"
        
        # Create Basic Auth header (official Sock Shop authentication method)
        credentials = f"{self.username}:{self.password}"
        base64_credentials = base64.b64encode(credentials.encode()).decode()
        self.auth_header = {"Authorization": f"Basic {base64_credentials}"}
        
        # Login to establish authenticated session
        self.client.get("/login", headers=self.auth_header, name="login")
    
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
    
    @task(4)  # ~3.7% - Checkout (triggers orders->payment->shipping flow)
    def checkout(self):
        """
        Create order using official Sock Shop method.
        Per official load test: clear cart, add item, then checkout.
        This triggers the full microservice chain: orders -> payment -> shipping
        Maintains EuroSys'24 methodology: 3.7% of actions create orders.
        """
        # Official Sock Shop pattern: clear cart first to avoid payment limit
        self.client.delete("/cart", name="clear_cart")
        
        # Add a single affordable item to cart
        item_id = random.choice(item_ids)
        self.client.post("/cart", json={"id": item_id, "quantity": 1}, name="add_for_checkout")
        
        # Create order (triggers orders -> payment -> shipping chain)
        self.client.post("/orders", headers=self.auth_header, name="checkout")

class StepLoad(LoadTestShape):
    """
    Step load pattern with sudden increases and decreases.
    EuroSys'24 Paper: Sudden traffic variations pattern.
    """
    
    def __init__(self):
        super().__init__()
        # Read duration from environment variable or use default
        import os
        duration_minutes = int(os.environ.get('LOCUST_RUN_TIME_MINUTES', '10'))
        self.test_duration = duration_minutes * 60  # Convert to seconds
        
        # Scale steps proportionally to total duration
        step_interval = self.test_duration / 5  # 5 steps
        self.steps = [
            (0, 100, 10),                              # Start
            (int(step_interval * 1), 200, 20),         # Step up at 20%
            (int(step_interval * 2), 100, 10),         # Step down at 40%
            (int(step_interval * 3), 300, 30),         # Step up to peak at 60%
            (int(step_interval * 4), 50, 5),           # Step down at 80%
        ]
    
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
