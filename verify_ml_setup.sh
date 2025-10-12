#!/bin/bash
# Verify ML Training Data Stream Setup
# This script checks if everything is properly configured

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}╔════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║  ML Training Data Stream - Setup Verification ║${NC}"
echo -e "${BLUE}╔════════════════════════════════════════════════╗${NC}"
echo ""

# Track status
ALL_GOOD=true

# Check 1: Docker
echo -e "${BLUE}[1/7]${NC} Checking Docker..."
if docker info > /dev/null 2>&1; then
    echo -e "  ${GREEN}✓${NC} Docker is running"
else
    echo -e "  ${RED}✗${NC} Docker is not running"
    ALL_GOOD=false
fi

# Check 2: Required files
echo -e "${BLUE}[2/7]${NC} Checking required files..."
FILES=(
    "realtime_ml_stream.py"
    "start_ml_stream.sh"
    "analyze_metrics.py"
    "ML_TRAINING_DATA.md"
    "QUICKSTART_ML_STREAM.md"
    "src/metrics-collector/app.py"
    "docker-compose.yml"
)

for file in "${FILES[@]}"; do
    if [ -f "$file" ]; then
        echo -e "  ${GREEN}✓${NC} $file"
    else
        echo -e "  ${RED}✗${NC} $file (missing)"
        ALL_GOOD=false
    fi
done

# Check 3: Scripts are executable
echo -e "${BLUE}[3/7]${NC} Checking script permissions..."
if [ -x "realtime_ml_stream.py" ] && [ -x "start_ml_stream.sh" ]; then
    echo -e "  ${GREEN}✓${NC} Scripts are executable"
else
    echo -e "  ${YELLOW}⚠${NC}  Scripts need execute permission"
    echo -e "     Run: chmod +x realtime_ml_stream.py start_ml_stream.sh"
fi

# Check 4: Python dependencies
echo -e "${BLUE}[4/7]${NC} Checking Python environment..."
if command -v python3 &> /dev/null; then
    echo -e "  ${GREEN}✓${NC} Python3 is available"
    
    # Check if script runs
    if python3 realtime_ml_stream.py --sample > /dev/null 2>&1; then
        echo -e "  ${GREEN}✓${NC} Streaming script works"
    else
        echo -e "  ${RED}✗${NC} Streaming script has errors"
        ALL_GOOD=false
    fi
else
    echo -e "  ${RED}✗${NC} Python3 is not installed"
    ALL_GOOD=false
fi

# Check 5: Docker services
echo -e "${BLUE}[5/7]${NC} Checking Docker services..."

# Check if any services are running
RUNNING_SERVICES=$(docker ps --format "{{.Names}}" | grep -E "(prometheus|metrics-collector|otel-collector)" || true)

if [ -z "$RUNNING_SERVICES" ]; then
    echo -e "  ${YELLOW}⚠${NC}  No services running yet"
    echo -e "     Run: docker-compose up -d"
else
    echo -e "  ${GREEN}✓${NC} Some services are running:"
    echo "$RUNNING_SERVICES" | while read service; do
        echo -e "     • $service"
    done
    
    # Check specific services
    if docker ps --format "{{.Names}}" | grep -q "prometheus"; then
        echo -e "  ${GREEN}✓${NC} Prometheus is running"
    else
        echo -e "  ${YELLOW}⚠${NC}  Prometheus is not running"
    fi
    
    if docker ps --format "{{.Names}}" | grep -q "metrics-collector"; then
        echo -e "  ${GREEN}✓${NC} Metrics collector is running"
    else
        echo -e "  ${YELLOW}⚠${NC}  Metrics collector is not running"
    fi
fi

# Check 6: Logs directory
echo -e "${BLUE}[6/7]${NC} Checking logs directory..."
if [ -d "logs" ]; then
    echo -e "  ${GREEN}✓${NC} logs/ directory exists"
    
    # Check if there are any log files
    LOG_COUNT=$(find logs -name "*.jsonl" 2>/dev/null | wc -l)
    if [ "$LOG_COUNT" -gt 0 ]; then
        echo -e "  ${GREEN}✓${NC} Found $LOG_COUNT JSONL file(s)"
    else
        echo -e "  ${YELLOW}ℹ${NC}  No JSONL files yet (this is normal)"
    fi
else
    echo -e "  ${YELLOW}⚠${NC}  logs/ directory doesn't exist"
    echo -e "     Creating it now..."
    mkdir -p logs
    echo -e "  ${GREEN}✓${NC} Created logs/ directory"
fi

# Check 7: Network connectivity
echo -e "${BLUE}[7/7]${NC} Checking network connectivity..."
if docker ps --format "{{.Names}}" | grep -q "prometheus"; then
    if curl -s http://localhost:9090/-/ready > /dev/null 2>&1; then
        echo -e "  ${GREEN}✓${NC} Prometheus is accessible"
    else
        echo -e "  ${YELLOW}⚠${NC}  Prometheus is not responding"
    fi
else
    echo -e "  ${YELLOW}ℹ${NC}  Prometheus not running (skipped)"
fi

echo ""
echo -e "${BLUE}════════════════════════════════════════════════${NC}"

# Summary
if [ "$ALL_GOOD" = true ]; then
    echo -e "${GREEN}✓ All checks passed!${NC}"
    echo ""
    echo -e "You're ready to start collecting ML training data!"
    echo ""
    echo -e "${BLUE}Next steps:${NC}"
    echo "  1. Start services:  docker-compose up -d"
    echo "  2. Start streaming: ./start_ml_stream.sh -o logs/training_data.jsonl"
    echo "  3. Generate load:   Open http://localhost:8089 (Locust)"
    echo ""
    echo -e "For help, see: ${BLUE}QUICKSTART_ML_STREAM.md${NC}"
else
    echo -e "${YELLOW}⚠ Some issues found${NC}"
    echo ""
    echo "Please address the issues above before proceeding."
    echo ""
    echo -e "For help, see: ${BLUE}SETUP_SUMMARY.md${NC}"
fi

echo -e "${BLUE}════════════════════════════════════════════════${NC}"
