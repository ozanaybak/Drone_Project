import dearpygui.dearpygui as dpg
import threading
import queue
from datetime import datetime
from src.drone.tcp_server import start_server as start_drone_server
from src.central_server.tcp_receiver import start_server as start_central_server
from src.common.queue_manager import data_queue
import src.drone.gui as drone_gui
import argparse
import yaml


def clear_dashboard_table(sender, app_data):
    print("[GUI] Clear Dashboard pressed")
    dpg.clear_table("central_table")

def poll_data():
    while True:
        print("poll_data: waiting for new data")
        sensor_data = data_queue.get()
        print(f"poll_data: received data: {sensor_data}")

        # GUI thread’inde çalışacak satır ekleme callback’i
        def _add_row(data=sensor_data):
            # select processed payload if tuple, else use data directly
            item = data[1] if isinstance(data, tuple) and len(data) > 1 else data
            print(f"[GUI] Adding row to central_table: {item}")
            dpg.add_table_row(
                "central_table",
                [ str(item.get(col, "")) 
                  for col in ["sensor_id","timestamp",
                              "temperature","humidity",
                              "average","std_dev",
                              "anomaly_flag"] ]
            )

        # Ana döngüye callback’i submit et
        dpg.invoke(_add_row)


def build_gui():
    with dpg.window(label="Unified Dashboard", width=1000, height=700):
        with dpg.child(label="Drone Panel", width=450, height=650, border=True):
            # Drone GUI’i oradan çağır
            drone_gui.build_drone_panel("Drone Panel")

        dpg.add_same_line()

        with dpg.child(label="Dashboard Panel", width=530, height=650, border=True):
            # Central‐server tablon
            with dpg.table(tag="central_table", header_row=True):
                for col in ["sensor_id","timestamp","temperature","humidity","average","std_dev","anomaly_flag"]:
                    dpg.add_table_column(label=col)
            dpg.add_button(label="Clear Dashboard", callback=clear_dashboard_table)
            dpg.add_separator()
            dpg.add_text("Server Log:", tag="ServerLogLabel")
            dpg.add_child_window(tag="CentralLog", width=-1, height=200)

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

    dpg.create_context()
    dpg.create_viewport(title="Unified Dashboard", width=1000, height=700)
    # Use manual callback management to integrate data polling
    dpg.configure_app(manual_callback_management=True)
    build_gui()
    # Launch the drone and central-server backends, then start polling for GUI updates
    threading.Thread(
        target=lambda: start_drone_server(drone_host, drone_port, central_host, central_port, data_queue),
        daemon=True
    ).start()
    threading.Thread(
        target=lambda: start_central_server(central_host, central_port, data_queue),
        daemon=True
    ).start()
    dpg.setup_dearpygui()
    dpg.show_viewport()

    # Main loop integrates GUI rendering and data polling
    import queue as _qp
    while dpg.is_dearpygui_running():
        # drain incoming data
        try:
            sensor_data = data_queue.get(block=False)
            item = sensor_data[1] if isinstance(sensor_data, tuple) and len(sensor_data) > 1 else sensor_data
            # add a new row using table_row context and text cells
            with dpg.table_row(parent="central_table"):
                for col in ["sensor_id","timestamp","temperature","humidity","average","std_dev","anomaly_flag"]:
                    dpg.add_text(str(item.get(col, "")))
            # log every received message
            log_msg = f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Received data: {item}"
            if item.get("anomaly_flag"):
                dpg.add_text(log_msg, parent="CentralLog", color=(255, 100, 100))
            else:
                dpg.add_text(log_msg, parent="CentralLog")
        except _qp.Empty:
            pass

        # process DearPyGui internal callbacks
        jobs = dpg.get_callback_queue()
        if jobs:
            dpg.run_callbacks(jobs)

        dpg.render_dearpygui_frame()

    dpg.destroy_context()