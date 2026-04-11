# PHCA - Proactive Holistic Context Aware Microservices Autoscaling

## Quick Start

### 1. Setup Environment
```bash
python scripts/setup_environment.py
```

### 2. Start Metrics Collection
```bash
# InfluxDB (recommended)
python collectors/phca_metrics_collector.py --duration 10

# CSV output
python collectors/phca_metrics_collector.py --collector csv --output results/metrics.csv
```

### 3. Start Load Testing
```bash
cd load-testing
python scripts/run_load_test.py --pattern constant
```

### 4. Monitor Live
```bash
python collectors/live_monitoring.py
```

## Architecture

```
PHCA Research Environment
├── Sock Shop (14 microservices)
├── InfluxDB (time-series database)
├── Grafana (visualization)
├── Load Testing (Locust)
└── Metrics Collection (custom)
```

## Directory Structure

```
PHCA/
├── collectors/           # Metrics collection scripts
├── docs/                # Documentation
├── scripts/             # Setup and utility scripts
├── results/             # Collected data
├── load-testing/        # Load generation
├── influx-stack/        # InfluxDB + Grafana
└── microservices-demo/  # Sock Shop application
```

## Services

### Sock Shop Microservices (14 services)
- **front-end**: Web interface
- **catalogue**: Product catalog
- **carts**: Shopping cart
- **orders**: Order processing
- **payment**: Payment processing
- **shipping**: Shipping service
- **user**: User management
- **queue-master**: Message processing
- **rabbitmq**: Message broker
- **edge-router**: Traffic routing
- **4 databases**: MongoDB/MySQL backends

### Monitoring Stack
- **InfluxDB**: Time-series database (port 8086)
- **Grafana**: Dashboards (port 3000)
- **Telegraf**: Metrics collector (when working)

## Access Points

- **Sock Shop**: http://localhost:80
- **Grafana**: http://localhost:3000 (admin/admin)
- **InfluxDB**: http://localhost:8086 (admin/password123)

## Data Collection

### Metrics per Service
- CPU percentage
- Memory usage/limit
- Network I/O (RX/TX bytes)
- Disk I/O (read/write bytes)
- Process count
- Container metadata

### Collection Frequency
- Default: Every 5 seconds
- Configurable via `--interval` parameter

## Load Testing Patterns

1. **Constant**: 50 users for 10 minutes
2. **Step**: 50→200→100→300→50 users
3. **Spike**: Flash crowds at intervals
4. **Ramp**: Organic growth 10→150→10

## Research Goals

- Proactive autoscaling using ML
- Context-aware resource management
- Holistic system optimization
- Microservices performance analysis