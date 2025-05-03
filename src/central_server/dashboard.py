import time
from src.common.logging_setup import get_logger

logger = get_logger('Dashboard')

def run_dashboard(buffer, interval: float = 2.0, display_count: int = 5):
    """
    Periodically prints the most recent entries from the CentralServer buffer.
    """
    logger.info("Dashboard started.")
    while True:
        data = list(buffer)
        if data:
            recent = data[-display_count:]
            logger.info(f"Last {display_count} entries: {recent}")
        else:
            logger.info("Buffer is empty.")
        time.sleep(interval)
