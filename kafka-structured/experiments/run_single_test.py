#!/usr/bin/env python3
"""
Single Test Runner for Validation
Runs a single experiment for testing purposes
"""

import argparse
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))

from run_experiments import execute_run
from run_config import ExperimentRun

def main():
    parser = argparse.ArgumentParser(description="Run single validation test")
    parser.add_argument("--condition", required=True, choices=["proactive", "reactive"],
                       help="Autoscaling condition to test")
    parser.add_argument("--pattern", required=True, choices=["constant", "step", "spike", "ramp"],
                       help="Load pattern to use")
    parser.add_argument("--run-id", type=int, default=999,
                       help="Run ID for output file (default: 999 for test)")
    
    args = parser.parse_args()
    
    print("="*80)
    print(f"SINGLE TEST RUN")
    print("="*80)
    print(f"Condition: {args.condition}")
    print(f"Pattern: {args.pattern}")
    print(f"Duration: 10 minutes load + 2 minutes settle")
    print(f"Run ID: {args.run_id}")
    print("="*80)
    print()
    
    # Create test run
    run = ExperimentRun(
        condition=args.condition,
        pattern=args.pattern,
        run_id=args.run_id
    )
    
    # Execute
    try:
        result = execute_run(run)
        
        if result:
            output_file = f"results/{args.condition}_{args.pattern}_run{args.run_id:02d}.jsonl"
            print()
            print("="*80)
            print(f"✓ Test completed successfully")
            print(f"✓ Output: {output_file}")
            print("="*80)
            
            # Print summary
            import json
            snapshots = []
            with open(output_file) as f:
                for line in f:
                    snapshots.append(json.loads(line))
            
            print(f"\nSnapshots collected: {len(snapshots)}")
            print(f"Services monitored: {len(snapshots[0]['services'])}")
            
            # Check for scaling actions
            services = list(snapshots[0]['services'].keys())
            scaling_events = 0
            for svc in services:
                prev_replicas = snapshots[0]['services'][svc]['replicas']
                for s in snapshots[1:]:
                    curr_replicas = s['services'][svc]['replicas']
                    if curr_replicas != prev_replicas:
                        scaling_events += 1
                        print(f"  Scaling: {svc} {prev_replicas} → {curr_replicas}")
                    prev_replicas = curr_replicas
            
            print(f"\nTotal scaling events: {scaling_events}")
            
            # Check for SLO violations
            violations = sum(1 for s in snapshots if any(m['slo_violated'] for m in s['services'].values()))
            print(f"SLO violations: {violations}/{len(snapshots)} intervals ({violations/len(snapshots)*100:.1f}%)")
            
            return 0
        else:
            print("\n✗ Test failed")
            return 1
            
    except Exception as e:
        print(f"\n✗ Error during test: {e}")
        import traceback
        traceback.print_exc()
        return 1

if __name__ == "__main__":
    sys.exit(main())
