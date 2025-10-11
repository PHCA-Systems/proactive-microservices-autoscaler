#!/usr/bin/env python3
"""
Simple analysis script for collected metrics data.
Provides insights into the training data for ML model development.
"""

import json
import pandas as pd
import numpy as np
from datetime import datetime
import argparse
import sys

def load_metrics_data(file_path):
    """Load metrics from JSONL file"""
    data = []
    try:
        with open(file_path, 'r') as f:
            for line in f:
                try:
                    data.append(json.loads(line.strip()))
                except json.JSONDecodeError:
                    continue
    except FileNotFoundError:
        print(f"File not found: {file_path}")
        return None
    
    if not data:
        print("No valid data found in file")
        return None
        
    return pd.DataFrame(data)

def analyze_data(df):
    """Perform basic analysis on the metrics data"""
    print("=== Metrics Data Analysis ===\n")
    
    # Basic info
    print(f"Total records: {len(df)}")
    print(f"Services: {', '.join(df['service'].unique())}")
    print(f"Time range: {df['timestamp'].min()} to {df['timestamp'].max()}")
    print(f"Collection duration: {pd.to_datetime(df['timestamp'].max()) - pd.to_datetime(df['timestamp'].min())}")
    print()
    
    # Service distribution
    print("=== Service Distribution ===")
    service_counts = df['service'].value_counts()
    for service, count in service_counts.items():
        print(f"{service}: {count} records")
    print()
    
    # Key metrics summary
    print("=== Key Metrics Summary ===")
    numeric_cols = ['rps', 'cpu_percent', 'memory_mb', 'latency_p95_ms', 'error_rate']
    
    for col in numeric_cols:
        if col in df.columns:
            print(f"\n{col}:")
            print(f"  Mean: {df[col].mean():.2f}")
            print(f"  Std:  {df[col].std():.2f}")
            print(f"  Min:  {df[col].min():.2f}")
            print(f"  Max:  {df[col].max():.2f}")
    
    # Per-service analysis
    print("\n=== Per-Service Analysis ===")
    for service in df['service'].unique():
        service_data = df[df['service'] == service]
        print(f"\n{service.upper()}:")
        print(f"  Records: {len(service_data)}")
        print(f"  Avg RPS: {service_data['rps'].mean():.1f}")
        print(f"  Avg CPU: {service_data['cpu_percent'].mean():.1f}%")
        print(f"  Avg Memory: {service_data['memory_mb'].mean():.1f} MB")
        print(f"  Avg Latency P95: {service_data['latency_p95_ms'].mean():.1f} ms")
        print(f"  Avg Error Rate: {service_data['error_rate'].mean():.3f}%")
    
    # Correlation analysis
    print("\n=== Correlation Analysis ===")
    correlation_cols = ['rps', 'cpu_percent', 'memory_mb', 'latency_p95_ms', 'active_connections']
    available_cols = [col for col in correlation_cols if col in df.columns]
    
    if len(available_cols) > 1:
        corr_matrix = df[available_cols].corr()
        print("Correlation matrix (values > 0.5 indicate strong correlation):")
        print(corr_matrix.round(3))
    
    # Potential scaling triggers
    print("\n=== Potential Scaling Triggers ===")
    high_cpu = df[df['cpu_percent'] > 80]
    high_memory = df[df['memory_utilization_percent'] > 80]
    high_latency = df[df['latency_p95_ms'] > 100]
    high_error = df[df['error_rate'] > 1.0]
    
    print(f"High CPU (>80%): {len(high_cpu)} records ({len(high_cpu)/len(df)*100:.1f}%)")
    print(f"High Memory (>80%): {len(high_memory)} records ({len(high_memory)/len(df)*100:.1f}%)")
    print(f"High Latency (>100ms): {len(high_latency)} records ({len(high_latency)/len(df)*100:.1f}%)")
    print(f"High Error Rate (>1%): {len(high_error)} records ({len(high_error)/len(df)*100:.1f}%)")
    
    # Data quality check
    print("\n=== Data Quality ===")
    print("Missing values per column:")
    missing = df.isnull().sum()
    for col, count in missing.items():
        if count > 0:
            print(f"  {col}: {count} ({count/len(df)*100:.1f}%)")
    
    if missing.sum() == 0:
        print("  No missing values found - excellent data quality!")

def export_for_ml(df, output_file):
    """Export processed data for ML training"""
    # Add derived features
    df_ml = df.copy()
    
    # Convert timestamp to features
    df_ml['timestamp'] = pd.to_datetime(df_ml['timestamp'])
    df_ml['hour'] = df_ml['timestamp'].dt.hour
    df_ml['day_of_week'] = df_ml['timestamp'].dt.dayofweek
    df_ml['minute'] = df_ml['timestamp'].dt.minute
    
    # Add rolling averages (if enough data)
    if len(df_ml) > 10:
        for col in ['rps', 'cpu_percent', 'memory_mb', 'latency_p95_ms']:
            if col in df_ml.columns:
                df_ml[f'{col}_rolling_5'] = df_ml.groupby('service')[col].rolling(5, min_periods=1).mean().reset_index(0, drop=True)
    
    # Add load indicators
    df_ml['is_high_load'] = (df_ml['cpu_percent'] > 70) | (df_ml['memory_utilization_percent'] > 70)
    df_ml['needs_scaling'] = (df_ml['cpu_percent'] > 80) | (df_ml['memory_utilization_percent'] > 80) | (df_ml['latency_p95_ms'] > 100)
    
    # Save to CSV for ML frameworks
    df_ml.to_csv(output_file, index=False)
    print(f"\nML-ready dataset exported to: {output_file}")
    print(f"Features: {len(df_ml.columns)} columns, {len(df_ml)} rows")

def main():
    parser = argparse.ArgumentParser(description='Analyze metrics data for ML training')
    parser.add_argument('file', help='Path to metrics JSONL file')
    parser.add_argument('--export-ml', help='Export processed data for ML training (CSV format)')
    parser.add_argument('--service', help='Analyze specific service only')
    
    args = parser.parse_args()
    
    # Load data
    df = load_metrics_data(args.file)
    if df is None:
        sys.exit(1)
    
    # Filter by service if specified
    if args.service:
        df = df[df['service'] == args.service]
        if len(df) == 0:
            print(f"No data found for service: {args.service}")
            sys.exit(1)
        print(f"Analyzing data for service: {args.service}\n")
    
    # Perform analysis
    analyze_data(df)
    
    # Export for ML if requested
    if args.export_ml:
        export_for_ml(df, args.export_ml)

if __name__ == "__main__":
    main()