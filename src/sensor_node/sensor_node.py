import socket
import time
import json
import argparse
import yaml
import random
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
            time.sleep(1)
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
    args = parser.parse_args()

    # Load configuration
    try:
        cfg = yaml.safe_load(open(args.config))
    except Exception as e:
        logger.error(f"Failed to load config: {e}")
        return

    drone_host = cfg.get('drone_host', '127.0.0.1')
    drone_port = cfg.get('drone_port', 9000)
    sensor_id = cfg.get('sensor_id', 'S1')
    send_interval = cfg.get('send_interval', 2)
    retries = cfg.get('retries', 3)

    logger.info(f"SensorNode {sensor_id} starting. Sending to {drone_host}:{drone_port}")
    while True:
        # Prepare payload with random sensor data
        payload = {
            "sensor_id": sensor_id,
            "timestamp": time.time(),
            "temperature": round(random.uniform(15.0, 30.0), 2),
            "humidity": round(random.uniform(30.0, 70.0), 2)
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