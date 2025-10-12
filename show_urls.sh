#!/bin/bash
# Show all important URLs for the demo

echo "╔════════════════════════════════════════════════════════════╗"
echo "║          OpenTelemetry Demo - Service URLs                ║"
echo "╚════════════════════════════════════════════════════════════╝"
echo ""

# Get Locust port
LOCUST_PORT=$(docker port load-generator 8089 2>/dev/null | cut -d: -f2)
if [ -n "$LOCUST_PORT" ]; then
    echo "🚀 Locust (Load Generator):"
    echo "   http://localhost:$LOCUST_PORT"
    echo "   Configure load testing and generate traffic"
    echo ""
fi

# Get Grafana port
GRAFANA_PORT=$(docker port grafana 3000 2>/dev/null | cut -d: -f2)
if [ -n "$GRAFANA_PORT" ]; then
    echo "📊 Grafana (Dashboards):"
    echo "   http://localhost:$GRAFANA_PORT"
    echo "   Username: admin | Password: admin"
    echo ""
fi

# Get Prometheus port
PROMETHEUS_PORT=$(docker port prometheus 9090 2>/dev/null | cut -d: -f2)
if [ -n "$PROMETHEUS_PORT" ]; then
    echo "📈 Prometheus (Metrics):"
    echo "   http://localhost:$PROMETHEUS_PORT"
    echo "   Query and explore metrics"
    echo ""
fi

# Get Jaeger port
JAEGER_PORT=$(docker port jaeger 16686 2>/dev/null | cut -d: -f2)
if [ -n "$JAEGER_PORT" ]; then
    echo "🔍 Jaeger (Tracing):"
    echo "   http://localhost:$JAEGER_PORT"
    echo "   View distributed traces"
    echo ""
fi

# Get Frontend port
FRONTEND_PORT=$(docker port frontend-proxy 8080 2>/dev/null | cut -d: -f2)
if [ -n "$FRONTEND_PORT" ]; then
    echo "🛒 Demo Application:"
    echo "   http://localhost:$FRONTEND_PORT"
    echo "   Browse the demo e-commerce site"
    echo ""
fi

echo "════════════════════════════════════════════════════════════"
echo ""
echo "💡 Tips:"
echo "  • Open Locust to generate load and see real metrics"
echo "  • Use './view_metrics.py --compact' for live metrics view"
echo "  • Use './start_ml_stream.sh -o logs/data.jsonl' to save data"
echo ""
