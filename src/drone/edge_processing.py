from collections import deque
import statistics
import time
from src.common.logging_setup import get_logger

logger = get_logger('EdgeProcessor')

class EdgeProcessor:
    """
    Processes incoming sensor payloads by computing a rolling average and
    anomaly flag based on a standard deviation threshold.
    """

    def __init__(self, window_size: int = 5, sigma_threshold: float = 2.0):
        self.window = deque(maxlen=window_size)
        self.sigma_threshold = sigma_threshold

    def process(self, payload: dict) -> dict:
        """
        Process the payload dictionary by:
        1. Appending the current temperature to the rolling window.
        2. Computing the average and standard deviation of the window.
        3. Determining if the latest temperature is an anomaly.
        4. Adding 'average', 'std_dev', 'anomaly_flag', and 'processed_timestamp'
           fields to the payload.
        Returns the updated payload.
        """
        temp = payload.get('temperature')
        if temp is None:
            logger.error("Payload missing 'temperature' field: %s", payload)
            return payload

        # Append to rolling window
        self.window.append(temp)

        # Compute metrics
        avg = statistics.mean(self.window)
        stddev = statistics.pstdev(self.window) if len(self.window) > 1 else 0.0

        # Determine anomaly: |temp - avg| > sigma_threshold * stddev
        anomaly = False
        if stddev > 0 and abs(temp - avg) > self.sigma_threshold * stddev:
            anomaly = True

        # Update payload
        payload.update({
            'average': round(avg, 2),
            'std_dev': round(stddev, 2),
            'anomaly_flag': anomaly,
            'processed_timestamp': time.time()
        })

        logger.debug(f"Processed payload with anomaly_flag: {payload}")

        if anomaly:
            logger.warning(f"Anomaly detected: temp={temp}, avg={avg}, stddev={stddev}")

        return payload