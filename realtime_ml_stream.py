#!/usr/bin/env python3
"""
Real-time ML Training Data Stream
Streams structured JSON metrics from all microservices in real-time.
Optimized for ML autoscaling model training.
"""

import subprocess
import json
import sys
import signal
import argparse
from datetime import datetime
from typing import Optional, TextIO

class RealtimeMetricsStream:
    """Stream real-time metrics from the metrics collector"""
    
    def __init__(self, output_file: Optional[str] = None, 
                 service_filter: Optional[str] = None,
                 pretty: bool = False):
        self.output_file = output_file
        self.service_filter = service_filter
        self.pretty = pretty
        self.file_handle: Optional[TextIO] = None
        self.process = None
        self.metrics_count = 0
        self.services_seen = set()
        
    def setup(self):
        """Setup output file if specified"""
        if self.output_file:
            self.file_handle = open(self.output_file, 'a', buffering=1)
            print(f"📊 Streaming metrics to: {self.output_file}", file=sys.stderr)
        
        print("🚀 Starting real-time metrics stream...", file=sys.stderr)
        if self.service_filter:
            print(f"🔍 Filtering for service: {self.service_filter}", file=sys.stderr)
        print("", file=sys.stderr)
        
    def cleanup(self):
        """Cleanup resources"""
        if self.file_handle:
            self.file_handle.close()
            print(f"\n✅ Saved {self.metrics_count} metrics to {self.output_file}", file=sys.stderr)
        
        if self.process:
            self.process.terminate()
            
        print(f"\n📈 Total metrics collected: {self.metrics_count}", file=sys.stderr)
        print(f"🏢 Services monitored: {', '.join(sorted(self.services_seen))}", file=sys.stderr)
        
    def process_line(self, line: str):
        """Process a single log line"""
        line = line.strip()
        if not line:
            return
            
        try:
            # Try to parse as JSON
            data = json.loads(line)
            
            # Skip if not a metrics record
            if 'service' not in data or 'timestamp' not in data:
                return
                
            # Apply service filter
            if self.service_filter and data.get('service') != self.service_filter:
                return
                
            # Track services
            self.services_seen.add(data.get('service', 'unknown'))
            self.metrics_count += 1
            
            # Output to stdout
            if self.pretty:
                print(json.dumps(data, indent=2))
            else:
                print(json.dumps(data, separators=(',', ':')))
            
            # Output to file if specified
            if self.file_handle:
                self.file_handle.write(json.dumps(data, separators=(',', ':')) + '\n')
                
        except json.JSONDecodeError:
            # Skip non-JSON lines (log messages, etc.)
            pass
        except Exception as e:
            print(f"⚠️  Error processing line: {e}", file=sys.stderr)
            
    def stream_from_docker(self, container_name: str = "metrics-collector"):
        """Stream logs from Docker container"""
        try:
            # Check if container is running
            check_cmd = ["docker", "ps", "--filter", f"name={container_name}", "--format", "{{.Names}}"]
            result = subprocess.run(check_cmd, capture_output=True, text=True)
            
            if container_name not in result.stdout:
                print(f"❌ Container '{container_name}' is not running!", file=sys.stderr)
                print(f"💡 Start it with: docker-compose up -d {container_name}", file=sys.stderr)
                return False
                
            # Stream logs
            cmd = ["docker", "logs", "-f", "--tail", "0", container_name]
            self.process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                universal_newlines=True,
                bufsize=1
            )
            
            print(f"✅ Connected to container: {container_name}", file=sys.stderr)
            print("📡 Streaming metrics in real-time...\n", file=sys.stderr)
            
            # Process lines as they come
            for line in iter(self.process.stdout.readline, ''):
                if not line:
                    break
                self.process_line(line)
                
            return True
            
        except KeyboardInterrupt:
            print("\n⏹️  Stopping stream...", file=sys.stderr)
            return True
        except Exception as e:
            print(f"❌ Error streaming logs: {e}", file=sys.stderr)
            return False
            
    def stream_from_stdin(self):
        """Stream logs from stdin"""
        try:
            print("📥 Reading metrics from stdin...", file=sys.stderr)
            
            for line in sys.stdin:
                if not line:
                    break
                self.process_line(line)
                
            return True
            
        except KeyboardInterrupt:
            print("\n⏹️  Stopping stream...", file=sys.stderr)
            return True

def print_sample_output():
    """Print sample output format"""
    sample = {
        "timestamp": "2024-10-12T18:27:45.123Z",
        "service": "cart",
        "rps": 120.4,
        "latency_p50_ms": 28.5,
        "latency_p95_ms": 42.1,
        "latency_p99_ms": 89.3,
        "latency_mean_ms": 31.2,
        "error_rate": 0.12,
        "success_rate": 99.88,
        "cpu_percent": 57.8,
        "memory_mb": 243.2,
        "memory_utilization_percent": 48.6,
        "disk_read_mb_per_sec": 0.8,
        "disk_write_mb_per_sec": 0.4,
        "disk_io_mb_per_sec": 1.2,
        "network_receive_mb_per_sec": 3.2,
        "network_transmit_mb_per_sec": 2.2,
        "network_io_mb_per_sec": 5.4,
        "active_connections": 15,
        "queue_depth": 3,
        "response_size_kb": 2.8,
        "request_size_kb": 1.2,
        "thread_count": 12,
        "heap_usage_mb": 180.5,
        "gc_collections_per_sec": 0.8,
        "gc_pause_time_ms": 2.1,
        "replica_count": 2,
        "target_cpu_utilization": 70.0,
        "target_memory_utilization": 70.0,
        "requests_per_connection": 8.03,
        "avg_response_time_ms": 31.2,
        "throughput_mb_per_sec": 0.33,
        "resource_efficiency_score": 1.89
    }
    
    print("\n📋 Sample Output Format:\n")
    print(json.dumps(sample, indent=2))
    print("\n" + "="*60)
    print("Metrics Categories:")
    print("  • Performance: RPS, latency percentiles, error rates")
    print("  • Resources: CPU, memory, disk I/O, network I/O")
    print("  • Application: connections, queue depth, threads, GC")
    print("  • Scaling: replica count, utilization targets")
    print("  • Derived: efficiency scores, throughput")
    print("="*60 + "\n")

def main():
    parser = argparse.ArgumentParser(
        description='Stream real-time metrics for ML autoscaling training',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Stream to console
  python realtime_ml_stream.py
  
  # Save to file
  python realtime_ml_stream.py -o training_data.jsonl
  
  # Filter specific service
  python realtime_ml_stream.py -s cart -o cart_metrics.jsonl
  
  # Pretty print for debugging
  python realtime_ml_stream.py --pretty
  
  # Read from stdin (for piping)
  docker logs -f metrics-collector | python realtime_ml_stream.py --stdin
        """
    )
    
    parser.add_argument('-o', '--output', 
                       help='Output file for metrics (JSONL format)')
    parser.add_argument('-s', '--service', 
                       help='Filter by specific service name')
    parser.add_argument('-c', '--container', 
                       default='metrics-collector',
                       help='Docker container name (default: metrics-collector)')
    parser.add_argument('--stdin', 
                       action='store_true',
                       help='Read from stdin instead of Docker logs')
    parser.add_argument('--pretty', 
                       action='store_true',
                       help='Pretty print JSON output')
    parser.add_argument('--sample', 
                       action='store_true',
                       help='Show sample output format and exit')
    
    args = parser.parse_args()
    
    # Show sample if requested
    if args.sample:
        print_sample_output()
        return 0
    
    # Create streamer
    streamer = RealtimeMetricsStream(
        output_file=args.output,
        service_filter=args.service,
        pretty=args.pretty
    )
    
    # Setup signal handlers
    def signal_handler(sig, frame):
        print("\n⏹️  Received interrupt signal", file=sys.stderr)
        streamer.cleanup()
        sys.exit(0)
    
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    try:
        streamer.setup()
        
        # Stream from appropriate source
        if args.stdin:
            success = streamer.stream_from_stdin()
        else:
            success = streamer.stream_from_docker(args.container)
            
        streamer.cleanup()
        return 0 if success else 1
        
    except Exception as e:
        print(f"❌ Fatal error: {e}", file=sys.stderr)
        streamer.cleanup()
        return 1

if __name__ == "__main__":
    sys.exit(main())
