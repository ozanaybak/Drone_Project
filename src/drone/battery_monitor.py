import threading
import time
from src.common.logging_setup import get_logger
import yaml

logger = get_logger('BatteryMonitor')

# Global callback function for GUI updates
battery_update_callback = None

def set_battery_callback(callback_fn):
    """Sets the GUI update callback function."""
    global battery_update_callback
    battery_update_callback = callback_fn

class BatteryMonitor(threading.Thread):
    """
    Simulates a drone battery that drains over time.
    When the battery level falls below or equal to 20%, it invokes the main callback
    and also optionally sends updates to a GUI callback if registered.
    """

    def __init__(self, callback, start_level: int = 100, drain_rate: int = 1, check_interval: float = 1.0):
        super().__init__(daemon=True)
        self.callback = callback
        self.level = start_level
        self.drain_rate = drain_rate
        self.check_interval = check_interval
        self._stop_event = threading.Event()
        self.paused = False

        # Load drone config file
        try:
            with open("config/drone_config.yaml") as f:
                cfg = yaml.safe_load(f)
        except Exception:
            cfg = {}

        self.pause_on_low_battery = cfg.get('pause_on_low_battery', False)

    def stop(self):
        """Stops the battery monitor thread."""
        self._stop_event.set()

    def run(self):
        logger.info(f"BatteryMonitor started: level={self.level}%, drain_rate={self.drain_rate}% per {self.check_interval} seconds")
        while not self._stop_event.is_set() and self.level > 0:
            time.sleep(self.check_interval)
            self.level = max(0, self.level - self.drain_rate)
            logger.debug(f"Battery level: {self.level}%")

            # Update GUI if callback is registered
            if battery_update_callback:
                battery_update_callback(self.level)

            if self.level <= 20:
                logger.warning(f"Battery low ({self.level}%), triggering RETURN_HOME")
                if self.pause_on_low_battery and not self.paused:
                    self.paused = True
                    logger.info("Pausing data forwarding due to low battery")
                self.callback(self.level)
            else:
                if self.paused:
                    self.paused = False
                    logger.info("Battery recovered, resuming data forwarding")

        logger.info("BatteryMonitor stopped at level=%d%%", self.level)

    def simulate_drain(self, percent: int):
        """
        Simulates draining the battery by a given percentage.
        Updates level, enforces bounds, and triggers callback if below threshold.
        """
        self.level = max(0, self.level - percent)
        logger.info(f"Simulated battery drain: new level={self.level}%")

        # Update GUI if callback is registered
        if battery_update_callback:
            battery_update_callback(self.level)

        # Trigger threshold callback if needed
        if self.level <= 20:
            logger.warning(f"Battery low ({self.level}%), triggering RETURN_HOME via simulate")
            if self.pause_on_low_battery and not self.paused:
                self.paused = True
                logger.info("Pausing data forwarding due to low battery (simulate)")
            self.callback(self.level)