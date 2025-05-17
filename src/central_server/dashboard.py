import time
from src.common.logging_setup import get_logger
from src.central_server.dashboard_gui import update_dashboard

logger = get_logger('Dashboard')


def run_dashboard(buffer, interval: float = 2.0, display_count: int = 5):
    """
    Periodically prints the most recent entries from the CentralServer buffer
    and updates the GUI dashboard.
    """
    logger.info("Dashboard started.")
    while True:
        data = list(buffer)
        if data:
            recent = data[-display_count:]
            logger.info(f"Last {display_count} entries: {recent}")
            for item in recent:
                update_dashboard(item)
        else:
            logger.info("Buffer is empty.")
        time.sleep(interval)


# Automated test runner for dashboard
def run_all_tests(queue):
    """
    Simulates sensor data and edge case scenarios for testing the Central Dashboard.
    """
    logger.info("Running automated dashboard tests...")

    # Normal data entries
    normal_data = [
        {"sensor_id": "S1", "temperature": 23.5, "humidity": 45.2, "timestamp": time.time(), "average": 22.5, "std_dev": 1.1, "anomaly_flag": False, "processed_timestamp": time.time()},
        {"sensor_id": "S2", "temperature": 25.0, "humidity": 55.1, "timestamp": time.time(), "average": 24.0, "std_dev": 1.5, "anomaly_flag": False, "processed_timestamp": time.time()},
        {"sensor_id": "S3", "temperature": 21.3, "humidity": 42.6, "timestamp": time.time(), "average": 22.0, "std_dev": 0.9, "anomaly_flag": False, "processed_timestamp": time.time()}
    ]

    for entry in normal_data:
        queue.append(entry)
        update_dashboard(entry)
        logger.info(f"Test - Normal data injected: {entry}")
        time.sleep(1)

    # Anomaly data
    anomaly = {
        "sensor_id": "S1",
        "temperature": 99.9,
        "humidity": 10.0,
        "timestamp": time.time(),
        "average": 22.0,
        "std_dev": 30.0,
        "anomaly_flag": True,
        "processed_timestamp": time.time()
    }
    queue.append(anomaly)
    update_dashboard(anomaly)
    logger.info("Test - Anomaly data injected.")
    time.sleep(1)

    # Simulate battery low
    logger.info("Test - Simulating low battery (<=20%)")
    update_dashboard({"sensor_id": "Battery", "temperature": 0, "humidity": 0, "timestamp": time.time(), "average": 0, "std_dev": 0, "anomaly_flag": False, "processed_timestamp": time.time()})
    time.sleep(1)

    # Simulate disconnection
    logger.info("Test - Simulating sensor disconnection.")
    update_dashboard({"sensor_id": "S2", "temperature": 0, "humidity": 0, "timestamp": time.time(), "average": 0, "std_dev": 0, "anomaly_flag": False, "processed_timestamp": time.time()})
    time.sleep(1)
