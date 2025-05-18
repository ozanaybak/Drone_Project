import threading
from datetime import datetime
from src.drone.tcp_server import start_server as start_drone_server
from src.central_server.tcp_receiver import start_server as start_central_server
from src.common.queue_manager import data_queue
import src.drone.gui as drone_gui
import argparse
import yaml
from collections import deque
from src.central_server.dashboard_gui import build_dashboard_panel
import tkinter as tk

# Rolling buffer: map sensor_id to deque of (timestamp, temperature)
rolling_buffers = {}
current_sensor = None


def build_gui():
    root = tk.Tk()
    root.title("Unified Dashboard")
    root.geometry("1000x700")

    drone_gui.build_drone_panel(root)
    update_dashboard, clear_dashboard = build_dashboard_panel(root)

    return update_dashboard, clear_dashboard, root


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Unified Dashboard and Servers")
    parser.add_argument('--drone-host',    type=str,   help='Drone server host')
    parser.add_argument('--drone-port',    type=int,   help='Drone server port')
    parser.add_argument('--central-host',  type=str,   help='Central server host')
    parser.add_argument('--central-port',  type=int,   help='Central server port')
    parser.add_argument('--log-level',     type=str,   choices=['DEBUG','INFO','WARNING','ERROR'], default='INFO', help='Logging level')
    parser.add_argument('--config',        type=str,   default='config/server_config.yaml', help='Path to central server config')
    args = parser.parse_args()

    try:
        cfg = yaml.safe_load(open(args.config))
    except Exception as e:
        print(f"Failed to load config: {e}")
        exit(1)

    drone_host   = args.drone_host or cfg.get('drone_host', '127.0.0.1')
    drone_port   = args.drone_port or cfg.get('drone_port', 9000)
    central_host = args.central_host or cfg.get('central_host', '127.0.0.1')
    central_port = args.central_port or cfg.get('central_port', 10000)

    from src.common.logging_setup import set_global_log_level
    set_global_log_level(args.log_level)

    # Initialize drone TCP server module-level placeholders
    import src.drone.tcp_server as drone_tcp
    from src.drone.edge_processing import EdgeProcessor
    from src.drone.battery_monitor import BatteryMonitor

    # Instantiate processor and battery monitor for drone module
    # These will be used by handle_client for anomaly detection
    drone_tcp.processor = EdgeProcessor(window_size=5, sigma_threshold=2.0)
    drone_tcp.battery_monitor = BatteryMonitor(
        callback=drone_tcp.on_battery_event,
        start_level=100,
        drain_rate=1,
        check_interval=1.0,
        )
    drone_tcp.battery_monitor.start()

    update_dashboard, clear_dashboard, root = build_gui()

    # Launch the drone and central-server backends
    threading.Thread(
        target=lambda: start_drone_server(drone_host, drone_port, central_host, central_port, data_queue),
        daemon=True
    ).start()
    threading.Thread(
        target=lambda: start_central_server(central_host, central_port, data_queue),
        daemon=True
    ).start()

    def poll_data():
        import queue as _qp
        try:
            while True:
                sensor_data = data_queue.get(block=False)
                item = sensor_data[1] if isinstance(sensor_data, tuple) and len(sensor_data) > 1 else sensor_data
                # update central dashboard table and anomaly log
                update_dashboard(item)
                # Update rolling buffer for this sensor
                buf = rolling_buffers.setdefault(item["sensor_id"], deque(maxlen=50))
                buf.append((item["timestamp"], item["temperature"]))
                # If this is the currently selected sensor, update chart
                global current_sensor
                if current_sensor == item["sensor_id"]:
                    buf = rolling_buffers[item["sensor_id"]]
                    times, temps = zip(*buf)
                    # Assuming update_dashboard handles chart updates internally
        except _qp.Empty:
            pass
        root.after(100, poll_data)

    root.after(100, poll_data)
    root.mainloop()