import pytest
import socket
import json
from src.sensor_node.sensor_node import send_data

class DummySocket:
    def __init__(self, response=b'{"status":"ACK"}'):
        self.response = response
        self.sent = b""
    def sendall(self, data):
        self.sent += data
    def recv(self, bufsize):
        return self.response
    def close(self):
        pass

def test_send_data_success(monkeypatch):
    dummy = DummySocket()
    monkeypatch.setattr(socket, "create_connection", lambda *args, **kwargs: dummy)
    payload = {"sensor_id": "S1", "timestamp": 0}
    result = send_data("h", 1, payload, retries=1)
    assert result is True
    assert dummy.sent.decode().startswith('{"sensor_id"')

def test_send_data_retries_and_fails(monkeypatch):
    calls = {"count": 0}
    def fail_connect(*args, **kwargs):
        calls["count"] += 1
        raise OSError("fail")
    monkeypatch.setattr(socket, "create_connection", fail_connect)
    result = send_data("h", 1, {"a":1}, retries=2)
    assert result is False
    assert calls["count"] == 2