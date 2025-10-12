#!/bin/bash

# Real-time metrics monitoring with better service-specific queries

echo "🔍 OpenTelemetry Demo - Real-time Service Metrics"
echo "================================================="
echo ""

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
CYAN='\033[0;36m'
NC='\033[0m'

# Function to get metrics with better error handling
get_metric() {
    local query="$1"
    local default_value="${2:-0}"
    
    response=$(curl -s "http://localhost:9090/api/v1/query?query=$query" 2>/dev/null)
    if [ $? -eq 0 ] && echo "$response" | jq -e '.data.result | length > 0' > /dev/null 2>&1; then
        echo "$response" | jq -r '.data.result[0].value[1]' 2>/dev/null | grep -v "null" || echo "$default_value"
    else
        echo "$default_value"
    fi
}

# Function to show service metrics
show_service_metrics() {
    local service="$1"
    local service_name="$2"
    
    echo -e "${CYAN}📊 $service_name${NC}"
    echo "----------------------------------------"
    
    # Get various metrics for this service
    local request_rate=$(get_metric "rate(traces_span_metrics_calls_total{service_name=\"$service\"}[5m])" "0")
    local error_rate=$(get_metric "rate(traces_span_metrics_calls_total{service_name=\"$service\",span_status_code=\"ERROR\"}[5m])" "0")
    local avg_duration=$(get_metric "histogram_quantile(0.95, rate(traces_span_metrics_duration_milliseconds_bucket{service_name=\"$service\"}[5m]))" "0")
    local total_calls=$(get_metric "sum(traces_span_metrics_calls_total{service_name=\"$service\"})" "0")
    
    # Format numbers nicely
    request_rate_formatted=$(printf "%.2f" "$request_rate" 2>/dev/null || echo "0")
    error_rate_formatted=$(printf "%.2f" "$error_rate" 2>/dev/null || echo "0")
    avg_duration_formatted=$(printf "%.0f" "$avg_duration" 2>/dev/null || echo "0")
    total_calls_formatted=$(printf "%.0f" "$total_calls" 2>/dev/null || echo "0")
    
    echo -e "  Requests/sec: ${GREEN}$request_rate_formatted${NC}"
    echo -e "  Error rate:   ${RED}$error_rate_formatted${NC}"
    echo -e "  Avg Duration: ${YELLOW}${avg_duration_formatted}ms${NC}"
    echo -e "  Total Calls:  ${BLUE}$total_calls_formatted${NC}"
    echo ""
}

# Function to show system metrics
show_system_metrics() {
    echo -e "${PURPLE}🖥️  System Metrics${NC}"
    echo "======================"
    
    # CPU usage
    cpu_usage=$(get_metric "rate(container_cpu_usage_seconds_total[5m]) * 100" "0")
    cpu_formatted=$(printf "%.1f" "$cpu_usage" 2>/dev/null || echo "0")
    echo -e "  CPU Usage: ${GREEN}${cpu_formatted}%${NC}"
    
    # Memory usage
    memory_usage=$(get_metric "container_memory_usage_bytes / container_spec_memory_limit_bytes * 100" "0")
    memory_formatted=$(printf "%.1f" "$memory_usage" 2>/dev/null || echo "0")
    echo -e "  Memory:    ${GREEN}${memory_formatted}%${NC}"
    
    # Network I/O
    network_in=$(get_metric "rate(container_network_receive_bytes_total[5m])" "0")
    network_out=$(get_metric "rate(container_network_transmit_bytes_total[5m])" "0")
    network_in_formatted=$(printf "%.1f" "$network_in" 2>/dev/null || echo "0")
    network_out_formatted=$(printf "%.1f" "$network_out" 2>/dev/null || echo "0")
    echo -e "  Network In:  ${BLUE}${network_in_formatted} B/s${NC}"
    echo -e "  Network Out: ${BLUE}${network_out_formatted} B/s${NC}"
    echo ""
}

# Function to show load generator stats
show_load_stats() {
    echo -e "${PURPLE}⚡ Load Generator${NC}"
    echo "=================="
    
    stats=$(curl -s http://localhost:32821/stats/requests 2>/dev/null)
    if [ $? -eq 0 ]; then
        current_rps=$(echo "$stats" | jq -r '.current_rps // 0' 2>/dev/null)
        total_requests=$(echo "$stats" | jq -r '.num_requests // 0' 2>/dev/null)
        failures=$(echo "$stats" | jq -r '.num_failures // 0' 2>/dev/null)
        users=$(echo "$stats" | jq -r '.user_count // 0' 2>/dev/null)
        
        echo -e "  Active Users: ${GREEN}$users${NC}"
        echo -e "  Current RPS:  ${GREEN}$current_rps${NC}"
        echo -e "  Total Reqs:   ${BLUE}$total_requests${NC}"
        echo -e "  Failures:     ${RED}$failures${NC}"
    else
        echo -e "  ${RED}Load generator not accessible${NC}"
    fi
    echo ""
}

# Function to show top endpoints
show_top_endpoints() {
    echo -e "${PURPLE}🔥 Top Endpoints${NC}"
    echo "==============="
    
    # Get top endpoints by call count
    response=$(curl -s "http://localhost:9090/api/v1/query?query=topk(5, sum by (span_name) (traces_span_metrics_calls_total))" 2>/dev/null)
    
    if [ $? -eq 0 ] && echo "$response" | jq -e '.data.result | length > 0' > /dev/null 2>&1; then
        echo "$response" | jq -r '.data.result[] | "  \(.metric.span_name): \(.value[1])"' | while read -r line; do
            echo -e "  ${GREEN}$line${NC}"
        done
    else
        echo -e "  ${YELLOW}No endpoint data available${NC}"
    fi
    echo ""
}

# Main monitoring loop
monitor_loop() {
    while true; do
        clear
        echo -e "${GREEN}$(date '+%Y-%m-%d %H:%M:%S')${NC}"
        echo ""
        
        show_load_stats
        show_system_metrics
        show_top_endpoints
        
        echo -e "${BLUE}📈 Service Metrics (Last 5 minutes)${NC}"
        echo "====================================="
        
        # Show metrics for each service
        show_service_metrics "frontend" "Frontend Service"
        show_service_metrics "cart" "Cart Service"
        show_service_metrics "checkout" "Checkout Service"
        show_service_metrics "product-catalog" "Product Catalog"
        show_service_metrics "payment" "Payment Service"
        show_service_metrics "shipping" "Shipping Service"
        show_service_metrics "recommendation" "Recommendation"
        show_service_metrics "ad" "Ad Service"
        show_service_metrics "currency" "Currency Service"
        
        echo -e "${BLUE}🔗 Quick Links${NC}"
        echo "=============="
        echo -e "  ${YELLOW}Grafana:${NC} http://localhost:8080/grafana/"
        echo -e "  ${YELLOW}Prometheus:${NC} http://localhost:9090"
        echo -e "  ${YELLOW}Load Generator:${NC} http://localhost:32821"
        echo -e "  ${YELLOW}Jaeger:${NC} http://localhost:16686"
        echo ""
        
        echo -e "${YELLOW}Press Ctrl+C to stop monitoring${NC}"
        echo -e "${CYAN}Refreshing in 15 seconds...${NC}"
        sleep 15
    done
}

# Check dependencies
if ! command -v jq &> /dev/null; then
    echo -e "${RED}Error: jq is not installed. Please install jq.${NC}"
    exit 1
fi

if ! curl -s http://localhost:9090/api/v1/query > /dev/null 2>&1; then
    echo -e "${RED}Error: Prometheus is not accessible at http://localhost:9090${NC}"
    exit 1
fi

echo -e "${GREEN}Starting real-time monitoring...${NC}"
echo -e "${YELLOW}Load generator is generating traffic to create metrics${NC}"
echo ""

# Start monitoring
monitor_loop
