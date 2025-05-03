import threading
import time
from src.common.logging_setup import get_logger

logger = get_logger('BatteryMonitor')

class BatteryMonitor(threading.Thread):
    """
    Simulates a drone battery that drains over time.
    When the battery level falls below or equal to 20%, it invokes the callback
    with an event 'RETURN_HOME' and the current battery level.
    """

    def __init__(self, callback, start_level: int = 100, drain_rate: int = 1, check_interval: float = 1.0):
        super().__init__(daemon=True)
        self.callback = callback
        self.level = start_level
        self.drain_rate = drain_rate
        self.check_interval = check_interval
        self._stop_event = threading.Event()

    def stop(self):
        """Stops the battery monitor thread."""
        self._stop_event.set()

    def run(self):
        self.check_interval = 3.0  
        logger.info(f"BatteryMonitor started: level={self.level}%, drain_rate={self.drain_rate}% per {self.check_interval} seconds")
        while not self._stop_event.is_set() and self.level > 0:
            time.sleep(self.check_interval)
            self.level = max(0, self.level - self.drain_rate)
            logger.debug(f"Battery level: {self.level}%")
            if self.level <= 20:
                logger.warning(f"Battery low ({self.level}%), triggering RETURN_HOME")
                self.callback('RETURN_HOME', self.level)
        logger.info("BatteryMonitor stopped at level=%d%%", self.level)
