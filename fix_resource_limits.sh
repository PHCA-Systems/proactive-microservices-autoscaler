#!/bin/bash
# Fix GKE Resource Limits to Match Data Collection Environment
# This increases CPU limits to prevent throttling and Locust timeouts

set -e

echo "=========================================="
echo "Updating Sock Shop Resource Limits"
echo "=========================================="
echo ""
echo "This will increase CPU limits from 100-500m to 1000m"
echo "to match the unlimited resources in Docker Compose"
echo "data collection environment."
echo ""

# Services to update (the 7 monitored services)
SERVICES=(
    "front-end"
    "carts"
    "orders"
    "catalogue"
    "user"
    "payment"
    "shipping"
)

NAMESPACE="sock-shop"

echo "Services to update:"
for svc in "${SERVICES[@]}"; do
    echo "  - $svc"
done
echo ""

read -p "Press ENTER to continue (or Ctrl+C to cancel): "
echo ""

# Update each service
for svc in "${SERVICES[@]}"; do
    echo "Updating $svc..."
    
    # Patch the deployment with new resource limits
    kubectl patch deployment "$svc" -n "$NAMESPACE" --type='json' -p='[
        {
            "op": "replace",
            "path": "/spec/template/spec/containers/0/resources",
            "value": {
                "limits": {
                    "cpu": "1000m",
                    "memory": "1Gi"
                },
                "requests": {
                    "cpu": "100m",
                    "memory": "200Mi"
                }
            }
        }
    ]'
    
    if [ $? -eq 0 ]; then
        echo "  ✓ $svc updated successfully"
    else
        echo "  ✗ Failed to update $svc"
    fi
    echo ""
done

echo "=========================================="
echo "Waiting for pods to restart..."
echo "=========================================="
echo ""

# Wait for all deployments to be ready
for svc in "${SERVICES[@]}"; do
    echo "Waiting for $svc..."
    kubectl rollout status deployment/"$svc" -n "$NAMESPACE" --timeout=5m
done

echo ""
echo "=========================================="
echo "✓ All services updated successfully!"
echo "=========================================="
echo ""
echo "New resource limits:"
echo "  CPU limit:    1000m (1 full core)"
echo "  Memory limit: 1Gi"
echo "  CPU request:  100m"
echo "  Memory request: 200Mi"
echo ""
echo "Next steps:"
echo "  1. Run validation test: python kafka-structured/experiments/run_single_test.py --condition reactive --pattern step --run-id 995"
echo "  2. Check Locust failure rate (should be <5%)"
echo "  3. If successful, run full experiment schedule"
echo ""
