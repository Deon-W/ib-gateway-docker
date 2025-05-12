# List available recipes
default:
    @just --list

# View live logs of the trading app container on prod
logs:
    ssh root@209.38.162.223 "cd ib-gateway-docker && docker-compose logs -f trading-app"

# View last N lines of logs (default: 100)
logs-tail n="100":
    ssh root@209.38.162.223 "cd ib-gateway-docker && docker-compose logs --tail={{n}} trading-app"

# Deploy code changes to prod
deploy files:
    scp {{files}} root@209.38.162.223:~/ib-gateway-docker/trading-app/ && \
    ssh root@209.38.162.223 "cd ib-gateway-docker && docker-compose restart trading-app"

# Restart both containers
restart:
    ssh root@209.38.162.223 "cd ib-gateway-docker && docker-compose restart trading-app ib-gateway"

# Stop all containers on prod
stop:
    ssh root@209.38.162.223 "cd ib-gateway-docker && docker-compose down"

# Start all containers on prod
start:
    ssh root@209.38.162.223 "cd ib-gateway-docker && docker-compose up -d"

# Check container status
status:
    ssh root@209.38.162.223 "cd ib-gateway-docker && docker-compose ps"

# View container resource usage
stats:
    ssh root@209.38.162.223 "docker stats"

# View error logs (last 100 lines)
errors:
    ssh root@209.38.162.223 "cd ib-gateway-docker && docker-compose logs --tail=100 trading-app | grep -i error"

# Save last 2 days of logs to a file (default: trading_logs_last_2_days.log)
logs-file output_file="trading_logs_last_2_days.log":
    ssh root@209.38.162.223 "cd ib-gateway-docker && docker-compose logs --timestamps trading-app | grep -E '$(date -v-2d +%Y-%m-%d)|$(date -v-1d +%Y-%m-%d)|$(date +%Y-%m-%d)'" > {{output_file}}

# Save last 4 hours of logs to a file (default: trading_logs_last_4hours.log)
logs-4h output_file="trading_logs_last_4hours.log":
    ssh root@209.38.162.223 "cd ib-gateway-docker && docker-compose logs --timestamps trading-app | grep -E '$(date -v-4H +%Y-%m-%d"T"%H)'" > {{output_file}}

# Deploy code changes and restart both containers
deploy-all files:
    scp {{files}} root@209.38.162.223:~/ib-gateway-docker/trading-app/ && \
    ssh root@209.38.162.223 "cd ib-gateway-docker && docker-compose restart trading-app ib-gateway"
