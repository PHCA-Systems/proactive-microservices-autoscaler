"""
Alternative approach: Run Locust in Docker to avoid Windows compilation issues.
This script provides Docker-based load generation as a workaround.
"""

import subprocess
import os
import sys

def run_locust_docker(host='http://host.docker.internal', locustfile='loadgen/locustfile.py', 
                     rps=10, duration=25, csv_path='logs/scratch/cola_lg'):
    """
    Run Locust in Docker container to avoid Windows build issues.
    
    Args:
        host: Target host (use host.docker.internal to access localhost from container)
        locustfile: Path to locustfile
        rps: Requests per second
        duration: Test duration in seconds
        csv_path: Path for CSV output (will be mounted in container)
    """
    # Ensure logs directory exists
    os.makedirs('logs/scratch', exist_ok=True)
    
    # Convert Windows paths to Unix-style for Docker
    locustfile_path = locustfile.replace('\\', '/')
    csv_path_clean = csv_path.replace('\\', '/')
    
    # Docker command
    cmd = [
        'docker', 'run', '--rm',
        '-v', f'{os.getcwd()}:/mnt/locust',
        '-w', '/mnt/locust',
        'locustio/locust:latest',
        '-f', f'/mnt/locust/{locustfile_path}',
        '--headless',
        '-u', str(rps),
        '-r', '100',
        '--host', host,
        '--run-time', f'{duration}s',
        '--csv-full-history',
        '--csv', f'/mnt/locust/{csv_path_clean}'
    ]
    
    print(f"Running Locust in Docker...")
    print(f"Command: {' '.join(cmd)}")
    print()
    
    try:
        result = subprocess.run(cmd, check=True, capture_output=False)
        print("\n✓ Load generation complete!")
        return True
    except subprocess.CalledProcessError as e:
        print(f"\n✗ Error running Locust in Docker: {e}")
        return False
    except FileNotFoundError:
        print("\n✗ Docker not found. Please install Docker Desktop.")
        print("  Or install Microsoft C++ Build Tools to compile Locust natively.")
        return False

if __name__ == '__main__':
    import argparse
    
    parser = argparse.ArgumentParser(description='Run Locust in Docker')
    parser.add_argument('--host', default='http://host.docker.internal', 
                       help='Target host URL')
    parser.add_argument('--rps', type=int, default=10, 
                       help='Requests per second')
    parser.add_argument('--duration', type=int, default=25, 
                       help='Test duration in seconds')
    parser.add_argument('--locustfile', default='loadgen/locustfile.py',
                       help='Path to locustfile')
    
    args = parser.parse_args()
    
    run_locust_docker(
        host=args.host,
        locustfile=args.locustfile,
        rps=args.rps,
        duration=args.duration
    )

