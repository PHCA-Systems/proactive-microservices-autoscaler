#!/bin/bash
# Run Kafka Pipeline Integration Tests
# This script starts Kafka infrastructure and runs integration tests

set -e

KAFKA_HOST="${KAFKA_BOOTSTRAP:-localhost:9092}"
SKIP_KAFKA_START="${SKIP_KAFKA_START:-false}"

echo "================================================================================"
echo "KAFKA PIPELINE INTEGRATION TEST RUNNER"
echo "================================================================================"
echo ""

# Check if Docker is available
if [ "$SKIP_KAFKA_START" != "true" ]; then
    echo "[INFO] Checking Docker availability..."
    
    if ! command -v docker &> /dev/null; then
        echo "[ERROR] Docker is not available"
        echo "[INFO] Please install Docker or set SKIP_KAFKA_START=true if Kafka is already running"
        exit 1
    fi
    
    echo "[OK] Docker is available: $(docker --version)"
    
    # Check if Kafka is already running
    echo "[INFO] Checking if Kafka is already running..."
    if docker ps --filter "name=kafka" --format "{{.Names}}" | grep -q "kafka"; then
        echo "[OK] Kafka is already running"
    else
        echo "[INFO] Starting Kafka infrastructure..."
        
        # Navigate to kafka-structured directory
        SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
        KAFKA_DIR="$(dirname "$SCRIPT_DIR")"
        
        cd "$KAFKA_DIR"
        
        # Start Zookeeper and Kafka
        echo "[INFO] Starting Zookeeper and Kafka containers..."
        docker-compose -f docker-compose.ml.yml up -d zookeeper kafka
        
        echo "[OK] Kafka containers started"
        
        # Wait for Kafka to be ready
        echo "[INFO] Waiting for Kafka to be ready (30 seconds)..."
        sleep 30
        
        echo "[OK] Kafka should be ready"
        
        cd "$SCRIPT_DIR"
    fi
else
    echo "[INFO] Skipping Kafka startup (using existing instance at $KAFKA_HOST)"
fi

# Check Python availability
echo ""
echo "[INFO] Checking Python availability..."

if ! command -v python3 &> /dev/null; then
    echo "[ERROR] Python 3 is not available"
    echo "[INFO] Please install Python 3.8 or higher"
    exit 1
fi

echo "[OK] Python is available: $(python3 --version)"

# Check if kafka-python is installed
echo "[INFO] Checking kafka-python package..."

if python3 -c "import kafka" 2>/dev/null; then
    echo "[OK] kafka-python is installed"
else
    echo "[WARN] kafka-python is not installed"
    echo "[INFO] Installing kafka-python..."
    
    SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
    pip3 install -r "$SCRIPT_DIR/requirements.txt"
    
    echo "[OK] kafka-python installed"
fi

# Run tests
echo ""
echo "[INFO] Running integration tests..."
echo ""

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TEST_SCRIPT="$SCRIPT_DIR/test_kafka_pipeline.py"

# Update Kafka host if needed
if [ "$KAFKA_HOST" != "localhost:9092" ]; then
    echo "[INFO] Using custom Kafka host: $KAFKA_HOST"
    export KAFKA_BOOTSTRAP="$KAFKA_HOST"
fi

python3 "$TEST_SCRIPT"
TEST_EXIT_CODE=$?

echo ""
if [ $TEST_EXIT_CODE -eq 0 ]; then
    echo "[SUCCESS] All tests passed!"
else
    echo "[FAILURE] Some tests failed"
fi

echo ""
echo "================================================================================"

exit $TEST_EXIT_CODE
