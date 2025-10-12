#!/bin/bash

# Colors
GREEN='\033[0;32m'
CYAN='\033[0;36m'
YELLOW='\033[1;33m'
BOLD='\033[1m'
NC='\033[0m' # No Color

echo -e "${BOLD}${CYAN}"
echo "╔════════════════════════════════════════════════════════╗"
echo "║         🚀 LOAD TESTING QUICK START                   ║"
echo "╚════════════════════════════════════════════════════════╝"
echo -e "${NC}"

echo -e "${YELLOW}This will start load generation and metrics viewing${NC}"
echo ""
echo -e "${CYAN}What to expect:${NC}"
echo "  • 30 concurrent users"
echo "  • ~30,000 total requests"
echo "  • Real-time metrics display"
echo "  • Takes ~10-15 minutes to complete"
echo ""

# Check if frontend is accessible
echo -e "${CYAN}Checking frontend...${NC}"
if curl -s -f http://localhost:8080/ > /dev/null 2>&1; then
    echo -e "${GREEN}✓ Frontend is accessible${NC}"
else
    echo -e "${YELLOW}⚠ Frontend may not be accessible${NC}"
    echo -e "${YELLOW}  Make sure Docker containers are running${NC}"
    exit 1
fi

echo ""
echo -e "${BOLD}${GREEN}Starting in 3 seconds...${NC}"
echo -e "${CYAN}Press Ctrl+C to stop at any time${NC}"
sleep 3

# Start metrics viewer in background
echo ""
echo -e "${CYAN}Starting metrics viewer...${NC}"
python3 view_docker_metrics.py &
METRICS_PID=$!

# Wait a bit for metrics viewer to initialize
sleep 3

# Start load generator
echo -e "${CYAN}Starting load generator...${NC}"
python3 generate_load.py

# When load generator finishes, keep metrics running for a bit
echo ""
echo -e "${GREEN}Load generation complete!${NC}"
echo -e "${CYAN}Metrics viewer will continue for 30 more seconds...${NC}"
sleep 30

# Stop metrics viewer
kill $METRICS_PID 2>/dev/null

echo ""
echo -e "${BOLD}${GREEN}✓ Load test complete!${NC}"
echo ""
