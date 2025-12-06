# How to View Logs

## View All Logs (All Services)
```powershell
docker-compose logs
```

## View Logs for Specific Service
```powershell
docker-compose logs front-end
docker-compose logs carts
docker-compose logs orders
docker-compose logs payment
docker-compose logs user
```

## Follow Logs in Real-Time (Like tail -f)
```powershell
docker-compose logs -f
```

## Follow Specific Service Logs
```powershell
docker-compose logs -f front-end
docker-compose logs -f carts
```

## View Last N Lines
```powershell
docker-compose logs --tail=100
docker-compose logs --tail=50 front-end
```

## View Logs with Timestamps
```powershell
docker-compose logs -t
docker-compose logs -f -t front-end
```

## View Logs for Multiple Services
```powershell
docker-compose logs front-end carts orders
```

## View Logs Since Specific Time
```powershell
docker-compose logs --since 10m
docker-compose logs --since 2024-12-06T15:00:00
```

## Using Docker Commands Directly
```powershell
docker logs docker-compose-front-end-1
docker logs docker-compose-front-end-1 -f
docker logs docker-compose-front-end-1 --tail=100
```

