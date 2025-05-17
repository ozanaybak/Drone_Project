import socket
import time
import json
import argparse
import yaml
import random
from datetime import datetime
from src.common.logging_setup import get_logger

logger = get_logger('SensorNode')

def send_data(host, port, payload, retries):
    """
    Attempts to send the JSON payload to the Drone TCP server.
    Retries up to 'retries' times on failure.
    Returns True on success, False if all attempts fail.
    """
    attempt = 0
    while attempt < retries:
        sock = None
        try:
            sock = socket.create_connection((host, port), timeout=5)
            message = json.dumps(payload).encode('utf-8')
            sock.sendall(message)
            response = sock.recv(1024)
            resp_text = response.decode('utf-8')
            logger.info(f"Received ACK from Drone: {resp_text}")
            return True
        except Exception as e:
            attempt += 1
            logger.warning(f"Send attempt {attempt}/{retries} failed: {e}")
            logger.info("Waiting 5 seconds before retry")
            time.sleep(5)
        finally:
            if sock:
                try:
                    sock.close()
                except Exception:
                    pass
    logger.error("All retry attempts failed.")
    return False

def main():
    parser = argparse.ArgumentParser(description="Sensor Node TCP Client")
    parser.add_argument('--config', required=True, help='Path to sensor_config.yaml')
    parser.add_argument('--drone-host', type=str, help='Drone TCP server IP address')
    parser.add_argument('--drone-port', type=int, help='Drone TCP server port')
    parser.add_argument('--sensor-id', type=str, help='Unique sensor ID')
    parser.add_argument('--interval', type=int, help='Data send interval in seconds')
    parser.add_argument('--retries', type=int, help='Number of retry attempts on failure')
    args = parser.parse_args()

    # Load configuration
    try:
        cfg = yaml.safe_load(open(args.config))
    except Exception as e:
        logger.error(f"Failed to load config: {e}")
        return

    drone_host = args.drone_host if args.drone_host else cfg.get('drone_host', '127.0.0.1')
    drone_port = args.drone_port if args.drone_port else cfg.get('drone_port', 9000)
    sensor_id = args.sensor_id if args.sensor_id else cfg.get('sensor_id', 'S1')
    send_interval = args.interval if args.interval else cfg.get('send_interval', 2)
    retries = args.retries if args.retries else cfg.get('retries', 3)

    # probability to inject an anomaly
    anomaly_prob = cfg.get('anomaly_probability', 0.1)

    logger.info(f"SensorNode {sensor_id} starting. Sending to {drone_host}:{drone_port}")
    while True:
        # Prepare payload with random sensor data, occasionally inject anomaly
        if random.random() < anomaly_prob:
            # Anomalous reading
            temperature = 1000.0
            humidity = 0.0
        else:
            # Normal reading
            temperature = round(random.uniform(15.0, 30.0), 2)
            humidity    = round(random.uniform(30.0, 70.0), 2)
        payload = {
            "sensor_id": sensor_id,
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "temperature": temperature,
            "humidity": humidity
        }
        logger.debug(f"Prepared payload: {payload}")
        success = send_data(drone_host, drone_port, payload, retries)
        if success:
            logger.info("Payload sent successfully")
        else:
            logger.error("Payload failed after retries")
        time.sleep(send_interval)

if __name__ == "__main__":
    main()