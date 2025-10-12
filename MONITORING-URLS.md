# 🔍 OpenTelemetry Demo - Monitoring URLs

## ✅ Working URLs

### **Primary Access (Through Frontend Proxy)**
- **Grafana**: http://localhost:8080/grafana/
- **Jaeger**: http://localhost:8080/jaeger/
- **Load Generator**: http://localhost:8080/loadgen/
- **Frontend App**: http://localhost:8080

### **Direct Access (Alternative URLs)**
- **Grafana**: http://localhost:32805
- **Prometheus**: http://localhost:9090
- **Load Generator**: http://localhost:32821
- **Jaeger**: http://localhost:16686

## 📊 Monitoring Tools

### **Real-time Terminal Monitoring**
```bash
./realtime-metrics.sh
```
- Updates every 15 seconds
- Shows per-service metrics
- Displays load generator stats
- Includes system metrics

### **Web-based Dashboard**
Open `metrics-dashboard.html` in your browser:
- Auto-refreshing dashboard
- Service health indicators
- Load generator statistics
- Direct links to all tools

### **Grafana Dashboards**
Access http://localhost:8080/grafana/ for:
- **Demo Dashboard**: Overview of all services
- **Spanmetrics Dashboard**: Detailed span analysis
- **APM Dashboard**: Application performance monitoring
- **NGINX Dashboard**: Frontend proxy metrics

## 🚀 Current Status

✅ **Load Generator**: 20 users generating traffic  
✅ **Prometheus**: Collecting metrics from all services  
✅ **Grafana**: Accessible with pre-configured dashboards  
✅ **Real-time Monitoring**: Multiple tools available  

## 🔧 Troubleshooting

If Grafana is not accessible:
1. Try the direct URL: http://localhost:32805
2. Check if containers are running: `docker-compose ps`
3. Check Grafana logs: `docker-compose logs grafana`

## 📈 Metrics Available

For each service:
- Request rate (requests/second)
- Error rate (errors/second)
- Response time (95th percentile)
- Total call count
- System metrics (CPU, memory, network)

---

**Note**: All URLs are updated in the monitoring scripts and web dashboard!
