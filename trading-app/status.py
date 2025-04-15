import sys
import logging
import docker

class Status:
    def __init__(self):
        self.current = "RUNNING"
        self.error_count = 0
        self.max_errors = 10
    
    def restart_services(self):
        try:
            logging.info("Restarting trading-app and ib-gateway services...")
            # Use Docker Python SDK to restart containers
            client = docker.from_env()
            
            # Restart IB Gateway first
            ib_container = client.containers.get('ib-gateway-docker-ib-gateway-1')
            ib_container.restart()
            logging.info("IB Gateway container restart initiated")
            
            # Then restart trading-app
            trading_container = client.containers.get('ib-gateway-docker-trading-app-1')
            trading_container.restart()
            logging.info("Trading app container restart initiated")
            
            logging.info("Restart commands sent successfully")
        except docker.errors.DockerException as e:
            logging.error(f"Failed to restart services: {str(e)}")
        finally:
            # Exit the container to ensure a clean restart
            sys.exit(1)
    
    def set_inactive(self):
        self.current = "INACTIVE"
        self.error_count += 1
        logging.warning(f"Status set to INACTIVE. Error count: {self.error_count}/{self.max_errors}")
        
        if self.error_count >= self.max_errors:
            logging.error(f"Maximum error count ({self.max_errors}) reached. Restarting services...")
            self.restart_services()
    
    def set_running(self):
        self.current = "RUNNING"
        if self.error_count > 0:
            logging.info(f"Status back to RUNNING. Resetting error count from {self.error_count} to 0")
        self.error_count = 0
    
    def get_status(self):
        return self.current

status = Status()