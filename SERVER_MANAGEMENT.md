# Server Management Guide

## Server Access

The trading application is hosted on a remote server with IP `209.38.162.223`. All commands should be executed from the project root directory.

### Basic Commands

1. **View Application Logs**
   ```bash
   # View live logs
   ssh root@209.38.162.223 "cd ib-gateway-docker && docker-compose logs -f trading-app"
   
   # View last N lines of logs
   ssh root@209.38.162.223 "cd ib-gateway-docker && docker-compose logs --tail=100 trading-app"
   ```

2. **Deploy Code Changes**
   ```bash
   # Copy a single file and restart the app
   scp trading-app/valr_ws.py root@209.38.162.223:~/ib-gateway-docker/trading-app/ && \
   ssh root@209.38.162.223 "cd ib-gateway-docker && docker-compose restart trading-app"
   
   # Copy multiple files and restart
   scp trading-app/{collector.py,valr_ws.py} root@209.38.162.223:~/ib-gateway-docker/trading-app/ && \
   ssh root@209.38.162.223 "cd ib-gateway-docker && docker-compose restart trading-app"
   ```

3. **Container Management**
   ```bash
   # Restart the trading app container
   ssh root@209.38.162.223 "cd ib-gateway-docker && docker-compose restart trading-app"
   
   # Stop all containers
   ssh root@209.38.162.223 "cd ib-gateway-docker && docker-compose down"
   
   # Start all containers
   ssh root@209.38.162.223 "cd ib-gateway-docker && docker-compose up -d"
   ```

4. **View Container Status**
   ```bash
   # Check container status
   ssh root@209.38.162.223 "cd ib-gateway-docker && docker-compose ps"
   
   # View container resource usage
   ssh root@209.38.162.223 "docker stats"
   ```

### Log Management

The application uses a two-layer logging system to prevent disk space issues:

1. **Docker-level Log Rotation**
   - Each container's logs are limited to 50MB per file
   - Keeps 7 rotated log files
   - Maximum log storage per container: 350MB (7 × 50MB)
   - Configured in docker-compose.yml

2. **System-level Log Rotation**
   - Rotates logs daily via logrotate
   - Compresses old logs
   - Triggers rotation at 50MB file size
   - Keeps 7 days of logs
   - Configured in /etc/logrotate.d/docker

#### Viewing Logs

1. **View Live Logs**
   ```bash
   # Follow live logs
   ssh root@209.38.162.223 "cd ib-gateway-docker && docker-compose logs -f trading-app"
   
   # View last N lines
   ssh root@209.38.162.223 "cd ib-gateway-docker && docker-compose logs --tail=100 trading-app"
   
   # View logs for a specific time period
   ssh root@209.38.162.223 "cd ib-gateway-docker && docker-compose logs --since '2025-04-13' trading-app"
   ```

2. **Check Log Disk Usage**
   ```bash
   # View disk space usage
   ssh root@209.38.162.223 "df -h"
   ```

### Troubleshooting

1. **Check IB Gateway Connection**
   ```bash
   # View IB Gateway logs
   ssh root@209.38.162.223 "cd ib-gateway-docker && docker-compose logs ib-gateway"
   
   # View recent errors only
   ssh root@209.38.162.223 "cd ib-gateway-docker && docker-compose logs ib-gateway | grep -i error"
   ```

2. **Restart Services After Connection Issues**
   ```bash
   # Restart both trading-app and ib-gateway
   ssh root@209.38.162.223 "cd ib-gateway-docker && docker-compose restart trading-app ib-gateway"
   ```

3. **View Application Errors**
   ```bash
   # View error logs
   ssh root@209.38.162.223 "cd ib-gateway-docker && docker-compose logs --tail=100 trading-app | grep -i error"
   ```

### Security Notes

1. Always use secure SSH connections
2. Keep your SSH keys secure and never share them
3. Regularly update server security patches
4. Monitor server access logs for any suspicious activity

### Best Practices

1. Always test changes locally before deploying to the server
2. Keep track of deployed changes
3. Monitor application logs regularly
4. Back up critical configuration files
5. Document any server configuration changes
