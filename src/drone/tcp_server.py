import socket
import threading
import json
import argparse
import yaml
import time
from src.common.logging_setup import get_logger
from src.drone.edge_processing import EdgeProcessor
from src.drone.battery_monitor import BatteryMonitor
from src.common.queue_manager import data_queue
from src.drone.gui import update_sensor_data



# Module-level placeholders for processor and battery monitor
processor: EdgeProcessor = None
battery_monitor: BatteryMonitor = None

logger = get_logger('DroneTCPServer')

def on_battery_event(level: int):
    """
    BatteryMonitor invokes this callback with the current battery level.
    """
    logger.warning(f"Battery low at level={level}%")

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

def handle_client(conn, addr, server_host, server_port, data_queue):
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

        # 1) Edge processing: compute anomaly_flag, average, std_dev
        try:
            processed = processor.process(payload.copy())
            logger.info(f"Processed payload: {processed}")
            import threading
            threading.Thread(target=update_sensor_data, args=(processed,), daemon=True).start()
            # Explicitly log the anomaly flag status
            if 'anomaly_flag' in processed:
                logger.info(f"anomaly_flag = {processed['anomaly_flag']}")
        except Exception as e:
            logger.error(f"Processing error: {e}")
            processed = payload

        # Debug full processed payload including anomaly_flag
        logger.debug(f"Processed payload with anomaly_flag: {processed}")

        # 2) Central Server’a ilet
        forward_to_central(processed, server_host, server_port)

        # Send data to GUI
        try:
            data_queue.put((payload, processed))
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

def start_server(host, port, server_host, server_port, data_queue):
    """
    Sensör bağlantılarını dinleyen TCP server’ı başlatır.
    """
    srv = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    # allow address reuse to avoid "address already in use" errors
    srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    srv.bind((host, port))
    srv.listen(5)
    logger.info(f"Sunucu dinlemede: {host}:{port}")

    while True:
        conn, addr = srv.accept()
        logger.debug(f"Accepted connection from {addr}, spawning handler thread")
        threading.Thread(
            target=handle_client,
            args=(conn, addr, server_host, server_port, data_queue),
            daemon=True
        ).start()

def start_server_from_gui(data_queue):
    """
    GUI tarafından çağrıldığında kullanılmak üzere TCP sunucusunu başlatır.
    """
    try:
        cfg = yaml.safe_load(open("config/drone_config.yaml"))
        logger.info("Loaded config from config/drone_config.yaml")
    except Exception as e:
        logger.error(f"Failed to load config: {e}")
        return

    global processor, battery_monitor

    drone_host    = cfg.get('drone_host',    '127.0.0.1')
    drone_port    = cfg.get('drone_port',    9000)
    server_host   = cfg.get('server_host',   '127.0.0.1')
    server_port   = cfg.get('server_port',   10000)
    window_size   = cfg.get('window_size',   5)
    sigma_thresh  = cfg.get('sigma_threshold',2.0)
    start_level   = cfg.get('start_level',   100)
    drain_rate    = cfg.get('drain_rate',    1)
    check_interval= cfg.get('check_interval',1.0)

    processor = EdgeProcessor(
        window_size=window_size,
        sigma_threshold=sigma_thresh
    )
    logger.info("EdgeProcessor initialized (via GUI).")

    battery_monitor = BatteryMonitor(
        callback=on_battery_event,
        start_level=start_level,
        drain_rate=drain_rate,
        check_interval=check_interval
    )
    battery_monitor.start()
    logger.info("BatteryMonitor started (via GUI).")

    start_server(drone_host, drone_port, server_host, server_port, data_queue)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Drone TCP Server")
    parser.add_argument('--config', required=True, help="Path to drone_config.yaml")
    parser.add_argument('--drone-host',       type=str,   help='Drone TCP server host')
    parser.add_argument('--drone-port',       type=int,   help='Drone TCP server port')
    parser.add_argument('--window-size',      type=int,   help='Rolling window size for edge processing')
    parser.add_argument('--sigma-threshold',  type=float, help='Sigma threshold for anomaly detection')
    parser.add_argument('--battery-threshold',type=int,   help='Battery low threshold percent')
    parser.add_argument('--pause-on-low-battery', action='store_true', help='Pause forwarding on low battery')
    args = parser.parse_args()


    # Load configuration
    cfg = yaml.safe_load(open(args.config))

    # Override settings
    host = args.drone_host or cfg.get('drone_host', '127.0.0.1')
    port = args.drone_port or cfg.get('drone_port', 9000)
    server_host = cfg.get('server_host', '127.0.0.1')
    server_port = cfg.get('server_port', 10000)
    window_size = args.window_size if args.window_size is not None else cfg.get('window_size', 5)
    sigma_threshold = args.sigma_threshold if args.sigma_threshold is not None else cfg.get('sigma_threshold', 2.0)
    battery_threshold = args.battery_threshold if args.battery_threshold is not None else cfg.get('battery_threshold', 20)
    pause_on_low_battery = args.pause_on_low_battery or cfg.get('pause_on_low_battery', False)

    # Initialize modules
    processor = EdgeProcessor(window_size=window_size, sigma_threshold=sigma_threshold)
    battery_monitor = BatteryMonitor(
        callback=on_battery_event,
        start_level=cfg.get('start_level', 100),
        drain_rate=cfg.get('drain_rate', 1),
        check_interval=cfg.get('check_interval', 1.0),
        pause_on_low_battery=pause_on_low_battery
    )
    battery_monitor.start()

    # Start server
    start_server(host, port, server_host, server_port, data_queue)