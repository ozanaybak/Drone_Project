import socket
import threading
import json
import argparse
import yaml
import time
from src.common.logging_setup import get_logger
from src.drone.edge_processing import EdgeProcessor
from src.drone.battery_monitor import BatteryMonitor
from queue import Queue
from tkinter import IntVar
from src.drone.gui import DroneGUI

logger = get_logger('DroneTCPServer')

# GUI setup
data_queue = Queue()
battery_var = IntVar()
gui_thread = DroneGUI(data_queue, battery_var)
gui_thread.start()

# Bu örnekler main() içinde başlatılacak
processor: EdgeProcessor = None
battery_monitor: BatteryMonitor = None

def on_battery_event(event: str, level: int):
    """
    BatteryMonitor %20’nin altına düştüğünde tetiklenen callback.
    """
    logger.warning(f"Battery event '{event}' at level={level}%")

def forward_to_central(payload: dict, host: str, port: int):
    """
    İşlenmiş payload’u Central Server’a TCP üzerinden gönderir.
    """
    logger.debug(f"Forwarding payload to central {host}:{port}")
    try:
        with socket.create_connection((host, port), timeout=5) as sock:
            sock.sendall(json.dumps(payload).encode('utf-8'))
            logger.info("Forwarded payload to central server")
    except Exception as e:
        logger.error(f"Failed to forward to central server: {e}")

def handle_client(conn, addr, server_host, server_port):
    """
    Her yeni sensör bağlantısı için:
    - JSON al, decode et
    - EdgeProcessor ile işle
    - Central Server’a ilet
    - Sensor’a ACK dön
    """
    logger.info(f"Yeni bağlantı: {addr}")
    try:
        data = conn.recv(4096)
        logger.debug(f"Raw data received: {data}")
        if not data:
            return
        payload = json.loads(data.decode('utf-8'))
        logger.info(f"Gelen payload: {payload}")

        # 1) Edge processing
        processed = processor.process(payload)
        logger.info(f"Processed payload: {processed}")

        # 2) Central Server’a ilet
        forward_to_central(processed, server_host, server_port)

        # Send data to GUI
        try:
            data_queue.put((payload, processed))
            battery_var.set(battery_monitor.level)
        except Exception as e:
            logger.error(f"Failed to update GUI: {e}")

        # 3) Sensor’a ACK
        ack = {"status": "ACK", "received_timestamp": time.time()}
        conn.sendall(json.dumps(ack).encode('utf-8'))
        logger.debug("ACK gönderildi.")
    except Exception as e:
        logger.error(f"handle_client hatası: {e}")
    finally:
        conn.close()

def start_server(host, port, server_host, server_port):
    """
    Sensör bağlantılarını dinleyen TCP server’ı başlatır.
    """
    srv = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    srv.bind((host, port))
    srv.listen(5)
    logger.info(f"Sunucu dinlemede: {host}:{port}")

    while True:
        conn, addr = srv.accept()
        logger.debug(f"Accepted connection from {addr}, spawning handler thread")
        threading.Thread(
            target=handle_client,
            args=(conn, addr, server_host, server_port),
            daemon=True
        ).start()

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Drone TCP Server")
    parser.add_argument('--config', required=True, help="Path to drone_config.yaml")
    args = parser.parse_args()

    # 1) Konfigürasyonu yükle
    try:
        cfg = yaml.safe_load(open(args.config))
        logger.info(f"Loaded config from {args.config}")
    except Exception as e:
        logger.error(f"Failed to load config: {e}")
        exit(1)

    drone_host    = cfg.get('drone_host',    '127.0.0.1')
    logger.debug(f"Drone host: {drone_host}")
    drone_port    = cfg.get('drone_port',    9000)
    logger.debug(f"Drone port: {drone_port}")
    server_host   = cfg.get('server_host',   '127.0.0.1')
    logger.debug(f"Server host: {server_host}")
    server_port   = cfg.get('server_port',   10000)
    logger.debug(f"Server port: {server_port}")
    window_size   = cfg.get('window_size',   5)
    sigma_thresh  = cfg.get('sigma_threshold',2.0)
    start_level   = cfg.get('start_level',   100)
    drain_rate    = cfg.get('drain_rate',    1)
    check_interval= cfg.get('check_interval',1.0)

    # 2) EdgeProcessor’i başlat
    processor = EdgeProcessor(
        window_size=window_size,
        sigma_threshold=sigma_thresh
    )
    logger.info("EdgeProcessor initialized.")

    # 3) BatteryMonitor’ü başlat
    battery_monitor = BatteryMonitor(
        callback=on_battery_event,
        start_level=start_level,
        drain_rate=drain_rate,
        check_interval=check_interval
    )
    battery_monitor.start()
    logger.info("BatteryMonitor started.")

    # 4) Sensör TCP server’ı çalıştır
    start_server(drone_host, drone_port, server_host, server_port)