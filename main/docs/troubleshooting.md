# PHCA Troubleshooting Guide

## Common Issues

### Docker Issues

#### "Docker is not running"
```bash
# Windows: Start Docker Desktop
# Linux: sudo systemctl start docker
```

#### "Permission denied" (Linux)
```bash
sudo usermod -aG docker $USER
# Logout and login again
```

### Sock Shop Issues

#### "Services not starting"
```bash
cd microservices-demo
docker-compose down
docker-compose up -d
```

#### "Port 80 already in use"
```bash
# Find process using port 80
netstat -ano | findstr :80
# Kill the process or change Sock Shop port
```

### InfluxDB Issues

#### "Connection refused"
```bash
# Check if InfluxDB is running
docker ps | grep influxdb

# Restart if needed
cd influx-stack
docker-compose restart influxdb
```

#### "No data in Grafana"
1. Check InfluxDB has data: http://localhost:8086
2. Verify Grafana data source: http://localhost:3000
3. Check time range in Grafana (set to "Last 1 hour")

### Metrics Collection Issues

#### "No containers found"
```bash
# Check if Sock Shop is running
docker ps | grep docker-compose

# Start Sock Shop if needed
cd microservices-demo
docker-compose up -d
```

#### "InfluxDB write failed"
```bash
# Check InfluxDB health
curl http://localhost:8086/health

# Restart InfluxDB
cd influx-stack
docker-compose restart influxdb
```

### Load Testing Issues

#### "Locust not found"
```bash
pip install locust
# or
pip install -r load-testing/requirements.txt
```

#### "Connection refused to Sock Shop"
```bash
# Check Sock Shop is accessible
curl http://localhost:80

# Check edge-router is running
docker ps | grep edge-router
```

## Performance Issues

### High CPU Usage
- Normal during load testing
- Monitor with: `python collectors/live_monitoring.py`

### High Memory Usage
- InfluxDB and Grafana use ~1-2GB combined
- Sock Shop uses ~2-3GB total
- Monitor with: `docker stats`

### Slow Response Times
- Expected during high load
- Check network: `docker network ls`
- Restart services if needed

## Data Issues

### Missing Metrics
```bash
# Check collector is running
python collectors/phca_metrics_collector.py --duration 1

# Verify data in InfluxDB
python scripts/test_grafana_connection.py
```

### Incomplete Data
- Some collections may fail during high load
- This is normal and expected
- 80%+ success rate is good

## Recovery Commands

### Full Reset
```bash
# Stop everything
docker-compose -f microservices-demo/docker-compose.yml down
docker-compose -f influx-stack/docker-compose.yml down

# Clean up
docker system prune -f

# Restart
python scripts/setup_environment.py
```

### Quick Restart
```bash
# Restart just the monitoring stack
cd influx-stack
docker-compose restart

# Restart just Sock Shop
cd microservices-demo
docker-compose restart
```