"""
Locust load testing file for Sock Shop microservices application.
This file defines the user behavior and tasks for load testing.
"""

from locust import HttpUser, task, between
import random

class SockShopUser(HttpUser):
    """
    Simulates a user browsing and shopping on the Sock Shop website.
    """
    wait_time = between(1, 3)  # Wait 1-3 seconds between tasks
    
    def on_start(self):
        """Called when a simulated user starts. Performs login/setup."""
        # Visit the homepage
        self.client.get("/", name="Homepage")
    
    @task(3)
    def browse_catalogue(self):
        """Browse the product catalogue - most common action."""
        # Get catalogue items
        self.client.get("/catalogue", name="Browse Catalogue")
        
        # Get a random item (assuming IDs 1-10)
        item_id = random.randint(1, 10)
        self.client.get(f"/catalogue/{item_id}", name="View Item")
    
    @task(2)
    def view_cart(self):
        """View shopping cart."""
        self.client.get("/cart", name="View Cart")
    
    @task(1)
    def add_to_cart(self):
        """Add an item to the shopping cart."""
        item_id = random.randint(1, 10)
        self.client.post(
            "/cart",
            json={"id": item_id, "quantity": 1},
            name="Add to Cart"
        )
    
    @task(1)
    def view_orders(self):
        """View order history."""
        self.client.get("/orders", name="View Orders")
    
    @task(1)
    def create_order(self):
        """Create a new order."""
        # First add item to cart
        item_id = random.randint(1, 10)
        self.client.post(
            "/cart",
            json={"id": item_id, "quantity": 1},
            name="Add to Cart (Order Flow)"
        )
        
        # Then create order
        self.client.post(
            "/orders",
            json={"items": [{"id": item_id, "quantity": 1}]},
            name="Create Order"
        )
    
    @task(1)
    def search(self):
        """Search for products."""
        search_term = random.choice(["sock", "red", "blue", "green", "wool", "cotton"])
        self.client.get(f"/catalogue?search={search_term}", name="Search Products")
    
    @task(1)
    def view_user_profile(self):
        """View user profile."""
        self.client.get("/user", name="View User Profile")

