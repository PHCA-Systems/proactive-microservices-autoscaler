#!/usr/bin/env python3
"""
Example: Using Collected Metrics for ML Analysis
Demonstrates how to load and analyze the JSON metrics data
"""

import json
import sys

def load_metrics(filename):
    """Load metrics from JSON file"""
    with open(filename, 'r') as f:
        return json.load(f)

def example_basic_analysis(data):
    """Example 1: Basic statistical analysis"""
    print("\n" + "="*80)
    print("EXAMPLE 1: Basic Statistical Analysis")
    print("="*80)
    
    snapshots = data['snapshots']
    
    # Extract time series data
    timestamps = [s['timestamp'] for s in snapshots]
    cpu_values = [s['summary']['total_cpu_percent'] for s in snapshots]
    memory_values = [s['summary']['total_memory_mb'] for s in snapshots]
    
    print(f"\nCollected {len(snapshots)} snapshots")
    print(f"Time range: {timestamps[0]} to {timestamps[-1]}")
    
    print(f"\nCPU Statistics:")
    print(f"  Min: {min(cpu_values):.2f}%")
    print(f"  Max: {max(cpu_values):.2f}%")
    print(f"  Avg: {sum(cpu_values)/len(cpu_values):.2f}%")
    
    print(f"\nMemory Statistics:")
    print(f"  Min: {min(memory_values):.2f} MB")
    print(f"  Max: {max(memory_values):.2f} MB")
    print(f"  Avg: {sum(memory_values)/len(memory_values):.2f} MB")

def example_service_analysis(data):
    """Example 2: Per-service analysis"""
    print("\n" + "="*80)
    print("EXAMPLE 2: Per-Service Analysis")
    print("="*80)
    
    snapshots = data['snapshots']
    
    # Get all services
    services = set()
    for snapshot in snapshots:
        services.update(snapshot['services']['microservices'].keys())
    
    print(f"\nAnalyzing {len(services)} services: {', '.join(sorted(services))}")
    
    # Analyze each service
    for service in sorted(services):
        cpu_values = []
        mem_values = []
        
        for snapshot in snapshots:
            if service in snapshot['services']['microservices']:
                svc_data = snapshot['services']['microservices'][service]
                cpu_values.append(svc_data['cpu_percent'])
                mem_values.append(svc_data['memory']['usage_mb'])
        
        if cpu_values:
            print(f"\n{service}:")
            print(f"  CPU: avg={sum(cpu_values)/len(cpu_values):.2f}%, "
                  f"max={max(cpu_values):.2f}%")
            print(f"  Memory: avg={sum(mem_values)/len(mem_values):.2f}MB, "
                  f"max={max(mem_values):.2f}MB")

def example_load_correlation(data):
    """Example 3: Correlate load with resource usage"""
    print("\n" + "="*80)
    print("EXAMPLE 3: Load vs Resource Correlation")
    print("="*80)
    
    snapshots = data['snapshots']
    
    # Filter snapshots with load data
    load_snapshots = [s for s in snapshots if s['load_generator']['available']]
    
    if not load_snapshots:
        print("\nNo load generator data available")
        return
    
    print(f"\nAnalyzing {len(load_snapshots)} snapshots with load data")
    
    # Extract data
    rps_values = [s['load_generator']['total_rps'] for s in load_snapshots]
    cpu_values = [s['summary']['total_cpu_percent'] for s in load_snapshots]
    p95_values = [s['load_generator']['response_time_percentiles']['p95'] 
                  for s in load_snapshots]
    
    # Simple correlation analysis
    print(f"\nLoad Metrics:")
    print(f"  RPS: min={min(rps_values):.1f}, max={max(rps_values):.1f}, "
          f"avg={sum(rps_values)/len(rps_values):.1f}")
    print(f"  P95 Latency: min={min(p95_values):.0f}ms, max={max(p95_values):.0f}ms, "
          f"avg={sum(p95_values)/len(p95_values):.0f}ms")
    
    print(f"\nResource Usage under Load:")
    print(f"  CPU: min={min(cpu_values):.1f}%, max={max(cpu_values):.1f}%, "
          f"avg={sum(cpu_values)/len(cpu_values):.1f}%")
    
    # Find peak load snapshot
    max_rps_idx = rps_values.index(max(rps_values))
    peak_snapshot = load_snapshots[max_rps_idx]
    
    print(f"\nPeak Load Snapshot ({peak_snapshot['timestamp']}):")
    print(f"  RPS: {peak_snapshot['load_generator']['total_rps']:.1f}")
    print(f"  Users: {peak_snapshot['load_generator']['user_count']}")
    print(f"  Total CPU: {peak_snapshot['summary']['total_cpu_percent']:.1f}%")
    print(f"  Total Memory: {peak_snapshot['summary']['total_memory_mb']:.1f}MB")
    print(f"  P95 Latency: {peak_snapshot['load_generator']['response_time_percentiles']['p95']:.0f}ms")

def example_anomaly_detection(data):
    """Example 4: Simple anomaly detection"""
    print("\n" + "="*80)
    print("EXAMPLE 4: Simple Anomaly Detection")
    print("="*80)
    
    snapshots = data['snapshots']
    
    # Calculate mean and std for CPU
    cpu_values = [s['summary']['total_cpu_percent'] for s in snapshots]
    mean_cpu = sum(cpu_values) / len(cpu_values)
    variance = sum((x - mean_cpu) ** 2 for x in cpu_values) / len(cpu_values)
    std_cpu = variance ** 0.5
    
    # Find anomalies (values > 2 standard deviations from mean)
    threshold = mean_cpu + (2 * std_cpu)
    
    print(f"\nCPU Anomaly Detection:")
    print(f"  Mean: {mean_cpu:.2f}%")
    print(f"  Std Dev: {std_cpu:.2f}%")
    print(f"  Threshold (mean + 2*std): {threshold:.2f}%")
    
    anomalies = []
    for snapshot in snapshots:
        cpu = snapshot['summary']['total_cpu_percent']
        if cpu > threshold:
            anomalies.append({
                'timestamp': snapshot['timestamp'],
                'cpu': cpu,
                'deviation': (cpu - mean_cpu) / std_cpu
            })
    
    if anomalies:
        print(f"\nFound {len(anomalies)} anomalies:")
        for anomaly in anomalies[:5]:  # Show first 5
            print(f"  {anomaly['timestamp']}: CPU={anomaly['cpu']:.2f}% "
                  f"({anomaly['deviation']:.2f} std devs)")
    else:
        print("\nNo anomalies detected")

def example_feature_extraction(data):
    """Example 5: Extract features for ML model"""
    print("\n" + "="*80)
    print("EXAMPLE 5: Feature Extraction for ML")
    print("="*80)
    
    snapshots = data['snapshots']
    
    print("\nExtracting features from each snapshot...")
    
    features = []
    for snapshot in snapshots:
        # Extract features
        feature_vector = {
            'timestamp': snapshot['timestamp'],
            'total_cpu': snapshot['summary']['total_cpu_percent'],
            'total_memory': snapshot['summary']['total_memory_mb'],
            'total_net_rx': snapshot['summary']['total_network_rx_mb'],
            'total_net_tx': snapshot['summary']['total_network_tx_mb'],
        }
        
        # Add load features if available
        if snapshot['load_generator']['available']:
            lg = snapshot['load_generator']
            feature_vector.update({
                'rps': lg['total_rps'],
                'users': lg['user_count'],
                'p95_latency': lg['response_time_percentiles']['p95'],
                'fail_ratio': lg['fail_ratio']
            })
        else:
            feature_vector.update({
                'rps': 0,
                'users': 0,
                'p95_latency': 0,
                'fail_ratio': 0
            })
        
        # Add per-service features (example: frontend)
        if 'frontend' in snapshot['services']['microservices']:
            frontend = snapshot['services']['microservices']['frontend']
            feature_vector.update({
                'frontend_cpu': frontend['cpu_percent'],
                'frontend_memory': frontend['memory']['usage_mb']
            })
        
        features.append(feature_vector)
    
    print(f"\nExtracted {len(features)} feature vectors")
    print(f"Features per vector: {len(features[0])}")
    print(f"\nFeature names: {', '.join(features[0].keys())}")
    
    # Show first feature vector as example
    print(f"\nExample feature vector (first snapshot):")
    for key, value in features[0].items():
        if key != 'timestamp':
            print(f"  {key}: {value}")
    
    return features

def main():
    if len(sys.argv) < 2:
        print("Usage: ./example_ml_usage.py <metrics.json>")
        print("\nFirst collect metrics with:")
        print("  ./collect_metrics_json.py -o metrics.json -d 60")
        sys.exit(1)
    
    filename = sys.argv[1]
    
    print("="*80)
    print("METRICS DATA ANALYSIS EXAMPLES")
    print("="*80)
    print(f"\nLoading data from: {filename}")
    
    try:
        data = load_metrics(filename)
        print(f"✓ Loaded {len(data['snapshots'])} snapshots")
        
        # Run examples
        example_basic_analysis(data)
        example_service_analysis(data)
        example_load_correlation(data)
        example_anomaly_detection(data)
        features = example_feature_extraction(data)
        
        # Optional: Save features to file
        output_file = filename.replace('.json', '_features.json')
        with open(output_file, 'w') as f:
            json.dump(features, f, indent=2)
        print(f"\n✓ Saved extracted features to: {output_file}")
        
        print("\n" + "="*80)
        print("NEXT STEPS")
        print("="*80)
        print("\n1. Use pandas for advanced analysis:")
        print("   import pandas as pd")
        print(f"   df = pd.read_json('{output_file}')")
        print("   df.describe()")
        
        print("\n2. Train ML models:")
        print("   from sklearn.ensemble import RandomForestRegressor")
        print("   # Use features to predict latency, detect anomalies, etc.")
        
        print("\n3. Visualize with matplotlib:")
        print("   import matplotlib.pyplot as plt")
        print("   df.plot(x='timestamp', y=['total_cpu', 'rps'])")
        
        print("\n4. Export to CSV for Excel/Tableau:")
        print(f"   ./metrics_analyzer.py {filename} --csv metrics.csv")
        
    except FileNotFoundError:
        print(f"\nError: File '{filename}' not found")
        print("\nCollect metrics first with:")
        print("  ./collect_metrics_json.py -o metrics.json -d 60")
        sys.exit(1)
    except Exception as e:
        print(f"\nError: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
