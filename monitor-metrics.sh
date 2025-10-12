#!/bin/bash

# Real-time metrics monitoring script for OpenTelemetry Demo services

echo "🔍 OpenTelemetry Demo - Real-time Metrics Monitor"
echo "=================================================="
echo ""

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to get service metrics
get_service_metrics() {
    local service_name="$1"
    local query="$2"
    local description="$3"
    
    echo -e "${BLUE}📊 $description${NC}"
    
    # Get current metrics from Prometheus
    response=$(curl -s "http://localhost:9090/api/v1/query?query=$query" 2>/dev/null)
    
    if [ $? -eq 0 ] && echo "$response" | jq -e '.data.result | length > 0' > /dev/null 2>&1; then
        value=$(echo "$response" | jq -r '.data.result[0].value[1]' 2>/dev/null)
        if [ "$value" != "null" ] && [ "$value" != "" ]; then
            echo -e "  ${GREEN}$service_name: $value${NC}"
        else
            echo -e "  ${YELLOW}$service_name: No data${NC}"
        fi
    else
        echo -e "  ${RED}$service_name: Error fetching data${NC}"
    fi
    echo ""
}

# Function to show service health
show_service_health() {
    echo -e "${BLUE}🏥 Service Health Status${NC}"
    echo "=========================="
    
    # Get targets from Prometheus
    targets=$(curl -s "http://localhost:9090/api/v1/targets" 2>/dev/null)
    
    if echo "$targets" | jq -e '.data.activeTargets | length > 0' > /dev/null 2>&1; then
        echo "$targets" | jq -r '.data.activeTargets[] | "\(.job): \(.health)"' | while read -r line; do
            if [[ $line == *"up"* ]]; then
                echo -e "  ${GREEN}✅ $line${NC}"
            else
                echo -e "  ${RED}❌ $line${NC}"
            fi
        done
    else
        echo -e "  ${RED}Error fetching target health${NC}"
    fi
    echo ""
}

# Function to show recent metrics
show_recent_metrics() {
    echo -e "${BLUE}📈 Recent Metrics (Last 5 minutes)${NC}"
    echo "===================================="
    
    # Get metrics for each service
    get_service_metrics "frontend" "rate(http_requests_total{job=\"frontend\"}[5m])" "Frontend Request Rate"
    get_service_metrics "cart" "rate(http_requests_total{job=\"cart\"}[5m])" "Cart Request Rate"
    get_service_metrics "checkout" "rate(http_requests_total{job=\"checkout\"}[5m])" "Checkout Request Rate"
    get_service_metrics "product-catalog" "rate(http_requests_total{job=\"product-catalog\"}[5m])" "Product Catalog Request Rate"
    get_service_metrics "payment" "rate(http_requests_total{job=\"payment\"}[5m])" "Payment Request Rate"
    get_service_metrics "shipping" "rate(http_requests_total{job=\"shipping\"}[5m])" "Shipping Request Rate"
    get_service_metrics "recommendation" "rate(http_requests_total{job=\"recommendation\"}[5m])" "Recommendation Request Rate"
    get_service_metrics "ad" "rate(http_requests_total{job=\"ad\"}[5m])" "Ad Service Request Rate"
    get_service_metrics "currency" "rate(http_requests_total{job=\"currency\"}[5m])" "Currency Request Rate"
}

# Function to show load generator status
show_load_generator_status() {
    echo -e "${BLUE}⚡ Load Generator Status${NC}"
    echo "=========================="
    
    # Check if load generator is running
    if curl -s http://localhost:32821/stats/requests > /dev/null 2>&1; then
        echo -e "  ${GREEN}✅ Load Generator is running${NC}"
        
        # Get load generator stats
        stats=$(curl -s http://localhost:32821/stats/requests 2>/dev/null)
        if [ $? -eq 0 ]; then
            current_users=$(echo "$stats" | grep -o '"current_rps": [0-9.]*' | cut -d' ' -f2)
            total_requests=$(echo "$stats" | grep -o '"num_requests": [0-9]*' | cut -d' ' -f2)
            failures=$(echo "$stats" | grep -o '"num_failures": [0-9]*' | cut -d' ' -f2)
            
            echo -e "  Current RPS: ${GREEN}$current_users${NC}"
            echo -e "  Total Requests: ${GREEN}$total_requests${NC}"
            echo -e "  Failures: ${RED}$failures${NC}"
        fi
    else
        echo -e "  ${YELLOW}⚠️  Load Generator not accessible${NC}"
    fi
    echo ""
}

# Function to show links
show_links() {
    echo -e "${BLUE}🔗 Monitoring Links${NC}"
    echo "=================="
    echo -e "  ${YELLOW}Prometheus:${NC} http://localhost:9090"
    echo -e "  ${YELLOW}Grafana:${NC} http://localhost:8080/grafana/ (or direct: http://localhost:32805)"
    echo -e "  ${YELLOW}Load Generator:${NC} http://localhost:32821"
    echo -e "  ${YELLOW}Jaeger:${NC} http://localhost:16686"
    echo -e "  ${YELLOW}Frontend:${NC} http://localhost:8080"
    echo ""
}

# Main monitoring loop
monitor_loop() {
    while true; do
        clear
        echo -e "${GREEN}$(date)${NC}"
        echo ""
        
        show_service_health
        show_load_generator_status
        show_recent_metrics
        show_links
        
        echo -e "${YELLOW}Press Ctrl+C to stop monitoring${NC}"
        echo "Refreshing in 10 seconds..."
        sleep 10
    done
}

# Check if jq is installed
if ! command -v jq &> /dev/null; then
    echo -e "${RED}Error: jq is not installed. Please install jq to run this script.${NC}"
    echo "Ubuntu/Debian: sudo apt-get install jq"
    echo "macOS: brew install jq"
    exit 1
fi

# Check if Prometheus is accessible
if ! curl -s http://localhost:9090/api/v1/query > /dev/null 2>&1; then
    echo -e "${RED}Error: Prometheus is not accessible at http://localhost:9090${NC}"
    echo "Please make sure Prometheus is running."
    exit 1
fi

# Start monitoring
monitor_loop
