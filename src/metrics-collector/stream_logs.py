#!/usr/bin/env python3
"""
Real-time log streaming script for metrics collector.
Streams metrics to stdout and optionally to files for ML training.
"""

import asyncio
import json
import sys
import os
from datetime import datetime
import argparse

class MetricsStreamer:
    def __init__(self, output_file=None, filter_service=None):
        self.output_file = output_file
        self.filter_service = filter_service
        self.file_handle = None
        
    async def start(self):
        """Initialize the streamer"""
        if self.output_file:
            self.file_handle = open(self.output_file, 'a')
            print(f"Streaming metrics to {self.output_file}")
        
    async def stop(self):
        """Cleanup resources"""
        if self.file_handle:
            self.file_handle.close()
            
    def process_log_line(self, line):
        """Process a single log line"""
        try:
            # Parse JSON log line
            data = json.loads(line.strip())
            
            # Filter by service if specified
            if self.filter_service and data.get('service') != self.filter_service:
                return
                
            # Add processing timestamp
            data['processed_at'] = datetime.utcnow().isoformat() + "Z"
            
            # Output to stdout
            print(json.dumps(data, separators=(',', ':')))
            
            # Output to file if specified
            if self.file_handle:
                self.file_handle.write(json.dumps(data, separators=(',', ':')) + '\n')
                self.file_handle.flush()
                
        except json.JSONDecodeError:
            # Skip non-JSON lines
            pass
        except Exception as e:
            print(f"Error processing line: {e}", file=sys.stderr)
            
    async def stream_from_docker_logs(self, container_name="metrics-collector"):
        """Stream logs from Docker container"""
        import subprocess
        
        cmd = ["docker", "logs", "-f", container_name]
        
        try:
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                universal_newlines=True,
                bufsize=1
            )
            
            print(f"Streaming logs from container: {container_name}")
            
            while True:
                line = process.stdout.readline()
                if not line:
                    break
                    
                self.process_log_line(line)
                
        except KeyboardInterrupt:
            print("\nStopping log stream...")
            process.terminate()
        except Exception as e:
            print(f"Error streaming logs: {e}", file=sys.stderr)
            
    async def stream_from_stdin(self):
        """Stream logs from stdin"""
        print("Reading metrics from stdin...")
        
        try:
            while True:
                line = sys.stdin.readline()
                if not line:
                    break
                    
                self.process_log_line(line)
                
        except KeyboardInterrupt:
            print("\nStopping stdin stream...")

def main():
    parser = argparse.ArgumentParser(description='Stream metrics collector logs')
    parser.add_argument('--output', '-o', help='Output file for metrics')
    parser.add_argument('--service', '-s', help='Filter by specific service')
    parser.add_argument('--container', '-c', default='metrics-collector', 
                       help='Docker container name (default: metrics-collector)')
    parser.add_argument('--stdin', action='store_true', 
                       help='Read from stdin instead of Docker logs')
    
    args = parser.parse_args()
    
    async def run():
        streamer = MetricsStreamer(args.output, args.service)
        
        try:
            await streamer.start()
            
            if args.stdin:
                await streamer.stream_from_stdin()
            else:
                await streamer.stream_from_docker_logs(args.container)
                
        finally:
            await streamer.stop()
    
    asyncio.run(run())

if __name__ == "__main__":
    main()