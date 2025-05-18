# Drone Edge Project

A prototype implementation of an edge‐processing pipeline for drone sensor data.  
This project demonstrates:

- **Sensor Node**: Generates and sends JSON payloads over TCP.  
- **Drone TCP Server**: Accepts sensor data, runs edge processing (rolling average, anomaly detection), simulates battery drain, forwards processed data to a central server, and (optionally) provides a live GUI.  
- **Central Server & Dashboard**: Buffers processed data in memory and periodically logs the most recent entries.  
- **Optional GUI**: A Tkinter window showing raw vs. processed data table and battery level.

---

## Prerequisites

- **macOS, Linux, or Windows**  
- **Python 3.8+** (with Tkinter support if using the GUI)  
- **git**, **pip**, **venv**  
- (Optional) **Wireshark** for network captures

---

## 1. Clone & Setup

```bash
# Clone the repository
git clone https://github.com/<your-username>/Drone-Project.git
cd Drone-Project

# Create and activate a virtual environment
python3 -m venv venv
source venv/bin/activate       # macOS/Linux
# .\venv\Scripts\activate      # Windows PowerShell

# Upgrade pip and install dependencies
pip install --upgrade pip
pip install -r requirements.txt
```

---

## 2. Configuration

Edit the YAML files in the `config/` directory as needed:

- **config/drone_config.yaml**
  ```yaml
  drone_host: "127.0.0.1"
  drone_port: 9000
  server_host: "127.0.0.1"
  server_port: 10000
  window_size: 5
  sigma_threshold: 2.0
  start_level: 100
  drain_rate: 1
  check_interval: 1.0
  ```

- **config/sensor_config.yaml**
  ```yaml
  drone_host: "127.0.0.1"
  drone_port: 9000

  sensor_id: "S1"
  send_interval: 2
  retries: 3
  ```

- **config/server_config.yaml**
  ```yaml
  server_host: "127.0.0.1"
  server_port: 10000
  ```

---

## 3. Running the System

You will run three core services (plus optionally multiple sensor nodes) in separate terminals:
# Optionally, use modular CLI command-based execution:
  python main.py --drone-host 127.0.0.1 --drone-port 9001 --central-host 127.0.0.1 --central-port 10001 --log-level INFO --config config/server_config.yaml
  python -m src.sensor_node.sensor_node --config config/sensor_S1.yaml --drone-host 127.0.0.1 --drone-port 9001 --sensor-id S1 --interval 1
  python -m src.sensor_node.sensor_node --config config/sensor_S2.yaml --drone-host 127.0.0.1 --drone-port 9001 --sensor-id S2 --interval 1

### A. Central Server & Dashboard

```bash
source venv/bin/activate
python -m src.central_server.tcp_receiver --config config/server_config.yaml
```

- Starts the TCP receiver and an in-process dashboard thread that logs the “Last 5 entries” every 2 seconds.
- Logs to console and `logs/centralserver.log`.

### B. Drone TCP Server

```bash
source venv/bin/activate
python -m src.drone.tcp_server --config config/drone_config.yaml
```

- Listens on `drone_host:drone_port` (default `127.0.0.1:9000`).
- Processes incoming sensor JSON, simulates battery, and forwards to central server.
- If Tkinter is available, opens a real-time GUI window.

### C. Sensor Node(s)

```bash
source venv/bin/activate
python -m src.sensor_node.sensor_node --config config/sensor_config.yaml
```

- Sends a JSON payload every `send_interval` seconds.
- Retries on failure up to `retries` times.
- You can run multiple instances with different `sensor_id` values for end-to-end testing.

---

## 4. Running Tests

Ensure your virtual environment is active, then:

```bash
pip install pytest
pytest -q
```

- **test_edge_processing.py**: Validates edge processing (rolling average, std dev, anomaly detection)  
- **test_sensor.py**: Tests sensor send/retry logic  
- **test_tcp.py**: End-to-end TCP buffering in the central server  

---

## 5. Logs & Troubleshooting

- All modules log to both console and rotating files in `logs/`:
  - `logs/sensornode.log`
  - `logs/dronetcpserver.log`
  - `logs/centralserver.log`

- If you see **Connection refused**, ensure the target service is already running.

- To capture network traffic on loopback (`lo0`):
  ```bash
  sudo tcpdump -i lo0 -w capture.pcap tcp port 9000 or tcp port 10000
  ```
  Open `capture.pcap` in Wireshark for inspection.

---

## License

This project is licensed under the [MIT License](LICENSE).