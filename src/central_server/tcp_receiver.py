import socket
import threading
import json
import argparse
import yaml
import time
from collections import deque
from threading import Thread
from src.common.logging_setup import get_logger
import queue

logger = get_logger('CentralServer')

# Global buffer to store received payloads
buffer = []

def handle_drone(conn, addr, output_queue):
    """
    incoming connections from the drone:
    - Receive JSON payload
    - Parse and append to buffer
    - Send back an ACK
    """
    logger.info(f"Connection from drone: {addr}")
    logger.debug("Waiting to receive data from drone")
    try:
        data = conn.recv(8192)
        logger.debug(f"Raw data received ({len(data)} bytes): {data}")
        if not data:
            return
        payload = json.loads(data.decode('utf-8'))
        print(f"[RECV] enqueue: {payload}")
        output_queue.put(payload)
        buffer.append(payload)
        logger.info(f"Buffered payload (size={len(buffer)}): {payload}")
        # Send ACK
        ack = {"status": "RECEIVED", "timestamp": time.time()}
        conn.sendall(json.dumps(ack).encode('utf-8'))
    except Exception as e:
        logger.error(f"Error handling drone data: {e}")
    finally:
        conn.close()

def start_server(host: str, port: int, output_queue: queue.Queue):
    """
    Start the TCP server to accept connections from the drone.
    """
    srv = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    srv.bind((host, port))
    srv.listen(5)
    logger.info(f"CentralServer listening on {host}:{port}")
    while True:
        conn, addr = srv.accept()
        logger.debug(f"Accepted connection from {addr}, spawning handler thread")
        threading.Thread(target=handle_drone, args=(conn, addr, output_queue), daemon=True).start()

def main():
    parser = argparse.ArgumentParser(description="Central Server TCP Receiver")
    parser.add_argument('--config', required=True, help='Path to server_config.yaml')
    args = parser.parse_args()

    # Load configuration
    try:
        cfg = yaml.safe_load(open(args.config))
        logger.info(f"Loaded config from {args.config}")
    except Exception as e:
        logger.error(f"Failed to load config: {e}")
        return

    server_host = cfg.get('server_host', '127.0.0.1')
    logger.debug(f"Central server host: {server_host}")
    server_port = cfg.get('server_port', 10000)
    logger.debug(f"Central server port: {server_port}")

    # dashboard will be driven by poll_data in main.py, so no thread launch here
    logger.info("Starting TCP server for drone data")
    start_server(server_host, server_port)

if __name__ == "__main__":
    main()