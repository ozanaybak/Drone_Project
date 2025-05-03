# Optional GUI support; disable if tkinter is unavailable
GUI_AVAILABLE = False
try:
    from queue import Queue
    import tkinter as tk
    from tkinter import IntVar
    from src.drone.gui import DroneGUI
    GUI_AVAILABLE = True
except ImportError:
    pass

import socket
import threading
import logging
from src.drone.battery_monitor import BatteryMonitor

logger = logging.getLogger('DroneTCPServer')

if GUI_AVAILABLE:
    data_queue = Queue()
    battery_var = IntVar()
    gui_thread = DroneGUI(data_queue, battery_var)
    gui_thread.start()
else:
    logger.warning("Tkinter not available; GUI disabled")

def handle_client(client_socket):
    battery_monitor = BatteryMonitor()
    while True:
        try:
            payload = client_socket.recv(1024)
            if not payload:
                break
            processed = process_payload(payload)
            battery_monitor.update_level(processed)
            if GUI_AVAILABLE:
                try:
                    data_queue.put((payload, processed))
                    battery_var.set(battery_monitor.level)
                except Exception as e:
                    logger.error(f"Failed to update GUI: {e}")
        except Exception as e:
            logger.error(f"Error handling client: {e}")
            break
    client_socket.close()

def process_payload(payload):
    # Dummy processing function
    return payload.decode('utf-8').strip()

def start_server(host='0.0.0.0', port=9999):
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.bind((host, port))
    server.listen(5)
    logger.info(f"Server started on {host}:{port}")
    while True:
        client_socket, addr = server.accept()
        logger.info(f"Accepted connection from {addr}")
        client_thread = threading.Thread(target=handle_client, args=(client_socket,))
        client_thread.start()
