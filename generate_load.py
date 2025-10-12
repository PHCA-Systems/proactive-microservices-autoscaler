#!/usr/bin/env python3
"""
Simple High-Load Generator
Generates HTTP traffic directly to test metrics collection
"""

import requests
import random
import time
import threading
from concurrent.futures import ThreadPoolExecutor
import sys

# ANSI colors
class Colors:
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    CYAN = '\033[96m'
    BOLD = '\033[1m'
    END = '\033[0m'

# Configuration
FRONTEND_URL = "http://localhost:8080"
NUM_WORKERS = 30  # Number of concurrent users
REQUESTS_PER_WORKER = 1000  # Each worker makes this many requests
DELAY_BETWEEN_REQUESTS = 0.5  # Seconds between requests per worker

# Products and categories from the demo
PRODUCTS = [
    "0PUK6V6EV0", "1YMWWN1N4O", "2ZYFJ3GM2N", "66VCHSJNUP",
    "6E92ZMYYFZ", "9SIQT8TOJO", "L9ECAV7KIM", "LS4PSXUNUM",
    "OLJCESPC7Z", "HQTGWGPNH4"
]

CATEGORIES = ["binoculars", "telescopes", "accessories", "assembly", "travel", "books"]

# Stats
stats = {
    'requests': 0,
    'success': 0,
    'errors': 0,
    'start_time': None
}
stats_lock = threading.Lock()

def update_stats(success=True):
    """Update request statistics"""
    with stats_lock:
        stats['requests'] += 1
        if success:
            stats['success'] += 1
        else:
            stats['errors'] += 1

def make_request(url, method='GET', **kwargs):
    """Make HTTP request with error handling"""
    try:
        if method == 'GET':
            response = requests.get(url, timeout=10, **kwargs)
        else:
            response = requests.post(url, timeout=10, **kwargs)
        
        success = response.status_code < 400
        update_stats(success)
        return success
    except Exception as e:
        update_stats(False)
        return False

def worker_task(worker_id):
    """Simulate a user browsing the site"""
    session = requests.Session()
    
    for i in range(REQUESTS_PER_WORKER):
        try:
            # Random action
            action = random.choice([
                'index', 'browse_product', 'browse_product', 'browse_product',
                'view_cart', 'get_recommendations', 'add_to_cart'
            ])
            
            if action == 'index':
                make_request(f"{FRONTEND_URL}/")
            
            elif action == 'browse_product':
                product = random.choice(PRODUCTS)
                make_request(f"{FRONTEND_URL}/api/products/{product}")
            
            elif action == 'get_recommendations':
                product = random.choice(PRODUCTS)
                make_request(f"{FRONTEND_URL}/api/recommendations", params={"productIds": [product]})
            
            elif action == 'view_cart':
                make_request(f"{FRONTEND_URL}/api/cart")
            
            elif action == 'add_to_cart':
                product = random.choice(PRODUCTS)
                quantity = random.randint(1, 5)
                make_request(
                    f"{FRONTEND_URL}/api/cart",
                    method='POST',
                    json={
                        "item": {"productId": product, "quantity": quantity},
                        "userId": f"user_{worker_id}"
                    }
                )
            
            # Small delay between requests
            time.sleep(DELAY_BETWEEN_REQUESTS)
            
        except Exception as e:
            update_stats(False)
    
    print(f"{Colors.CYAN}Worker {worker_id} completed{Colors.END}")

def print_stats():
    """Print current statistics"""
    while True:
        time.sleep(5)
        
        with stats_lock:
            elapsed = time.time() - stats['start_time']
            rps = stats['requests'] / elapsed if elapsed > 0 else 0
            success_rate = (stats['success'] / stats['requests'] * 100) if stats['requests'] > 0 else 0
            
            print(f"\n{Colors.BOLD}{'='*60}{Colors.END}")
            print(f"{Colors.GREEN}Total Requests: {stats['requests']}{Colors.END}")
            print(f"{Colors.GREEN}Success: {stats['success']}{Colors.END}")
            print(f"{Colors.RED}Errors: {stats['errors']}{Colors.END}")
            print(f"{Colors.CYAN}RPS: {rps:.1f} req/s{Colors.END}")
            print(f"{Colors.YELLOW}Success Rate: {success_rate:.1f}%{Colors.END}")
            print(f"{Colors.BOLD}{'='*60}{Colors.END}\n")

def main():
    print(f"{Colors.BOLD}{Colors.GREEN}")
    print("╔" + "═" * 58 + "╗")
    print("║" + " " * 15 + "HIGH-LOAD GENERATOR" + " " * 24 + "║")
    print("╚" + "═" * 58 + "╝")
    print(Colors.END)
    
    print(f"\n{Colors.CYAN}Configuration:{Colors.END}")
    print(f"  Workers: {NUM_WORKERS}")
    print(f"  Requests per worker: {REQUESTS_PER_WORKER}")
    print(f"  Total requests: {NUM_WORKERS * REQUESTS_PER_WORKER}")
    print(f"  Delay between requests: {DELAY_BETWEEN_REQUESTS}s")
    print(f"  Target: {FRONTEND_URL}")
    
    # Test connection
    print(f"\n{Colors.YELLOW}Testing connection to frontend...{Colors.END}")
    try:
        response = requests.get(FRONTEND_URL, timeout=5)
        print(f"{Colors.GREEN}✓ Frontend is accessible{Colors.END}")
    except Exception as e:
        print(f"{Colors.RED}✗ Cannot connect to frontend: {e}{Colors.END}")
        print(f"{Colors.YELLOW}Make sure the frontend is running at {FRONTEND_URL}{Colors.END}")
        return
    
    print(f"\n{Colors.GREEN}Starting load generation in 3 seconds...{Colors.END}")
    time.sleep(3)
    
    stats['start_time'] = time.time()
    
    # Start stats printer thread
    stats_thread = threading.Thread(target=print_stats, daemon=True)
    stats_thread.start()
    
    # Start workers
    print(f"\n{Colors.BOLD}Spawning {NUM_WORKERS} workers...{Colors.END}\n")
    
    try:
        with ThreadPoolExecutor(max_workers=NUM_WORKERS) as executor:
            futures = [executor.submit(worker_task, i) for i in range(NUM_WORKERS)]
            
            # Wait for all to complete
            for future in futures:
                future.result()
        
        print(f"\n{Colors.GREEN}{Colors.BOLD}✓ Load generation completed!{Colors.END}")
        
        # Final stats
        with stats_lock:
            elapsed = time.time() - stats['start_time']
            rps = stats['requests'] / elapsed if elapsed > 0 else 0
            success_rate = (stats['success'] / stats['requests'] * 100) if stats['requests'] > 0 else 0
            
            print(f"\n{Colors.BOLD}{'='*60}{Colors.END}")
            print(f"{Colors.CYAN}FINAL STATISTICS{Colors.END}")
            print(f"{Colors.BOLD}{'='*60}{Colors.END}")
            print(f"Total Requests: {Colors.GREEN}{stats['requests']}{Colors.END}")
            print(f"Successful: {Colors.GREEN}{stats['success']}{Colors.END}")
            print(f"Errors: {Colors.RED}{stats['errors']}{Colors.END}")
            print(f"Duration: {Colors.CYAN}{elapsed:.1f}s{Colors.END}")
            print(f"Average RPS: {Colors.CYAN}{rps:.1f} req/s{Colors.END}")
            print(f"Success Rate: {Colors.YELLOW}{success_rate:.1f}%{Colors.END}")
            print(f"{Colors.BOLD}{'='*60}{Colors.END}\n")
    
    except KeyboardInterrupt:
        print(f"\n{Colors.YELLOW}⏹️  Stopping load generation...{Colors.END}")
        print(f"{Colors.GREEN}Partial results saved{Colors.END}\n")

if __name__ == "__main__":
    main()
