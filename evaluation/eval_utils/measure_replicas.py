"""
Measure replica counts over time and write to service_replicas_count.json
This script runs in the background and periodically records replica counts.
"""

import json
import time
import sys
import os
from datetime import datetime, timezone

# Add parent directory to path to import utils
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))
import utils.kube as kube_utils

def measure_replicas_loop(interval=1):
    """
    Continuously measure replica counts and write to JSON file.
    Writes one JSON object per line (JSONL format).
    """
    output_file = 'service_replicas_count.json'
    
    # Clear or create the file
    if os.path.exists(output_file):
        # Append mode to continue existing measurements
        file_mode = 'a'
    else:
        file_mode = 'w'
    
    try:
        with open(output_file, file_mode) as f:
            while True:
                try:
                    # Get current deployments
                    deployments = kube_utils.get_current_deployments()
                    
                    # Create measurement record
                    record = {
                        'timestamp': datetime.now(timezone.utc).isoformat(),
                        'replicas': deployments
                    }
                    
                    # Write as JSON line
                    f.write(json.dumps(record) + '\n')
                    f.flush()  # Ensure data is written immediately
                    
                    # Wait for next measurement
                    time.sleep(interval)
                    
                except KeyboardInterrupt:
                    break
                except Exception as e:
                    print(f"Error measuring replicas: {e}", file=sys.stderr)
                    time.sleep(interval)
                    
    except Exception as e:
        print(f"Error opening output file: {e}", file=sys.stderr)
        sys.exit(1)

if __name__ == '__main__':
    # Default interval: measure every 1 second
    interval = float(sys.argv[1]) if len(sys.argv) > 1 else 1.0
    measure_replicas_loop(interval)

