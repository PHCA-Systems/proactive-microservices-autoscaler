#!/bin/bash
# Start real-time ML metrics streaming
# This script ensures all services are running and starts the metrics stream

set -e

echo "🚀 Starting ML Training Data Stream"
echo "===================================="
echo ""

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check if Docker is running
if ! docker info > /dev/null 2>&1; then
    echo -e "${RED}❌ Docker is not running${NC}"
    exit 1
fi

# Check if metrics-collector is running
if ! docker ps --filter "name=metrics-collector" --format "{{.Names}}" | grep -q "metrics-collector"; then
    echo -e "${YELLOW}⚠️  Metrics collector is not running${NC}"
    echo "Starting metrics collector..."
    docker-compose up -d metrics-collector
    echo "Waiting for metrics collector to start..."
    sleep 5
fi

# Check if Prometheus is running
if ! docker ps --filter "name=prometheus" --format "{{.Names}}" | grep -q "prometheus"; then
    echo -e "${YELLOW}⚠️  Prometheus is not running${NC}"
    echo "Starting Prometheus..."
    docker-compose up -d prometheus
    echo "Waiting for Prometheus to start..."
    sleep 5
fi

echo -e "${GREEN}✅ All required services are running${NC}"
echo ""

# Parse command line arguments
OUTPUT_FILE=""
SERVICE_FILTER=""
PRETTY=""

while [[ $# -gt 0 ]]; do
    case $1 in
        -o|--output)
            OUTPUT_FILE="$2"
            shift 2
            ;;
        -s|--service)
            SERVICE_FILTER="$2"
            shift 2
            ;;
        --pretty)
            PRETTY="--pretty"
            shift
            ;;
        -h|--help)
            echo "Usage: $0 [OPTIONS]"
            echo ""
            echo "Options:"
            echo "  -o, --output FILE    Save metrics to file"
            echo "  -s, --service NAME   Filter by service name"
            echo "  --pretty             Pretty print JSON output"
            echo "  -h, --help           Show this help message"
            echo ""
            echo "Examples:"
            echo "  $0                                    # Stream to console"
            echo "  $0 -o training_data.jsonl            # Save to file"
            echo "  $0 -s cart -o cart_metrics.jsonl    # Filter by service"
            exit 0
            ;;
        *)
            echo "Unknown option: $1"
            echo "Use -h or --help for usage information"
            exit 1
            ;;
    esac
done

# Build command
CMD="python3 realtime_ml_stream.py"

if [ -n "$OUTPUT_FILE" ]; then
    CMD="$CMD -o $OUTPUT_FILE"
    echo "📁 Output file: $OUTPUT_FILE"
fi

if [ -n "$SERVICE_FILTER" ]; then
    CMD="$CMD -s $SERVICE_FILTER"
    echo "🔍 Service filter: $SERVICE_FILTER"
fi

if [ -n "$PRETTY" ]; then
    CMD="$CMD $PRETTY"
fi

echo ""
echo "📡 Starting real-time metrics stream..."
echo "Press Ctrl+C to stop"
echo ""

# Run the streaming script
exec $CMD
