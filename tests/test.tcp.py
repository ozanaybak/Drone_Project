import threading
import socket
import json
import time
import pytest
from src.central_server.tcp_receiver import start_server, buffer

SERVER_HOST = "127.0.0.1"
SERVER_PORT = 11000

@pytest.fixture(scope="module", autouse=True)
def server_thread():
    t = threading.Thread(target=start_server, args=(SERVER_HOST, SERVER_PORT), daemon=True)
    t.start()
    time.sleep(0.5)  # Give server time to start
    yield
    # Daemon thread will exit with the test process

def test_tcp_receive_and_buffering():
    data = {"sensor_id": "S1", "timestamp": 0}
    with socket.create_connection((SERVER_HOST, SERVER_PORT), timeout=1) as sock:
        sock.sendall(json.dumps(data).encode('utf-8'))
        resp = sock.recv(1024)
        assert b"RECEIVED" in resp
    time.sleep(0.1)
    assert len(buffer) >= 1
    last = buffer[-1]
    assert last["sensor_id"] == "S1"