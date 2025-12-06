"""
Example usage of the LoadGenerator for Sock Shop.
This script demonstrates how to use the LoadGenerator to test the application.
"""

import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from loadgen.load_generator import LoadGenerator

def main():
    # Initialize the load generator
    # Adjust host if your Sock Shop is running on a different URL
    lg = LoadGenerator(
        host='http://localhost',  # Sock Shop front-end (edge-router on port 80)
        locustfile='loadgen/locustfile.py',
        duration=25,  # Run for 25 seconds
        csv_path='logs/scratch/cola_lg',
        num_workers=10,
        hatch_rate=100,
        latency_threshold=100,  # 100ms latency threshold
        w_i=5,  # Weight for action cost
        w_l=10,  # Weight for latency constraint
        lat_opt='Average Latency'
    )
    
    print("=" * 60)
    print("Sock Shop Load Generator Example")
    print("=" * 60)
    print(f"Target: {lg.host}")
    print(f"Duration: {lg.duration}s")
    print(f"Latency Threshold: {lg.latency_threshold}ms")
    print("=" * 60)
    print()
    
    # Example 1: Generate load at a specific RPS
    print("Example 1: Generate load at 10 RPS")
    print("-" * 60)
    lg.generate_load(rps=10)
    stats = lg.read_load_statistics(rps=10)
    print("Statistics:")
    for key, value in stats.items():
        print(f"  {key}: {value}")
    print()
    
    # Example 2: Evaluate QoE
    print("Example 2: Evaluate Quality of Experience")
    print("-" * 60)
    qoe, stats = lg.eval_qoe(rps=10, action=0)
    print(f"QoE Score: {qoe}")
    print(f"Average Latency: {stats.get('Average Latency', 'N/A')} ms")
    print(f"95th Percentile Latency: {stats.get('95p Latency', 'N/A')} ms")
    print()
    
    # Example 3: Run a workload sequence
    print("Example 3: Run workload sequence [5, 10, 20] RPS")
    print("-" * 60)
    rps_rates = [5, 10, 20]
    print(f"Running workload with RPS rates: {rps_rates}")
    print("This will take approximately {} seconds...".format(
        lg.duration * len(rps_rates) + 5
    ))
    
    results = lg.run_workload(rps_rates)
    
    print("\nWorkload Results:")
    for result in results:
        print(f"\nIteration {result['iter']}:")
        print(f"  RPS Rate: {result['rps_rate']}")
        print(f"  Average Latency: {result['perf'].get('Average Latency', 'N/A')} ms")
        print(f"  95p Latency: {result['perf'].get('95p Latency', 'N/A')} ms")
        print(f"  Output RPS: {result['perf'].get('Output RPS', 'N/A')}")
        print(f"  Services: {result.get('services', {})}")
        if result.get('replicas'):
            print(f"  Replica measurements: {len(result['replicas'])} samples")
    
    print("\n" + "=" * 60)
    print("Load generation complete!")
    print("=" * 60)
    print("\nOutput files:")
    print(f"  - Statistics: {lg.csv_path}.csv_stats.csv")
    print(f"  - History: {lg.csv_path}.csv_stats_history.csv")
    print(f"  - Replicas: service_replicas_count.json")

if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nLoad generation interrupted by user.")
        sys.exit(0)
    except Exception as e:
        print(f"\nError: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        sys.exit(1)

