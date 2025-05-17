__all__ = [
    "update_sensor_data",
    "create_context",
    "create_viewport",
    "build_gui",
    "setup_dearpygui",
    "show_viewport",
    "start_dearpygui",
    "destroy_context",
    "is_dearpygui_running"
]
import subprocess
import os
from dearpygui.dearpygui import *
from datetime import datetime
import random
import threading
import time
from queue import Queue
import src.common as shared_data  # assume shared data_queue is here
import src.drone.tcp_server as tcp_server

# anomaly threshold and log
anomaly_threshold = 1.0
anomaly_log = []

battery_level = 100
sensor_data_log = []

def simulate_battery_drain(sender, app_data, user_data):
    global battery_level
    drain = random.randint(5, 15)
    battery_level = max(0, battery_level - drain)
    set_value("BatteryProgress", battery_level / 100.0)
    log_msg = f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Battery drained to {battery_level}%"
    add_text(log_msg, parent="LogScroll")
    if battery_level <= 20:
        set_value("StatusText", "Returning to Base")
    else:
        set_value("StatusText", "Normal Operation")

def update_sensor_data(sensor_data):
    """Append incoming sensor data, compute anomaly, and update GUI."""
    global sensor_data_log, anomaly_log
    # determine anomaly based on threshold or existing flag
    threshold = get_value("AnomalyThreshold")
    anomaly_flag = sensor_data.get("anomaly_flag", False) or sensor_data["temperature"] > threshold
    sensor_data["anomaly_flag"] = anomaly_flag
    sensor_data_log.append(sensor_data)

    # add a new row to the sensor table
    with table_row(parent="SensorTable"):
        add_text(sensor_data["sensor_id"])
        add_text(str(sensor_data["temperature"]))
        add_text(str(sensor_data["humidity"]))
        add_text(str(sensor_data["timestamp"]))
        add_text(str(sensor_data.get("average", "")))
        add_text(str(sensor_data.get("std_dev", "")))
        add_text("⚠" if anomaly_flag else "")

    # logging panel
    log_msg = f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Data from {sensor_data['sensor_id']} received"
    add_text(log_msg, parent="LogScroll")

    # if anomaly, add to anomaly list
    if anomaly_flag:
        anomaly_log.append(sensor_data)
        anomaly_msg = f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Anomaly: {sensor_data['sensor_id']} value {sensor_data['temperature']}"
        add_text(anomaly_msg, parent="AnomalyList")

def build_drone_panel(parent):
    with child_window(parent=parent, tag="DronePanel", width=450, height=650, border=True):
        add_text("Drone Edge GUI", tag="MainLabel")

        with table(tag="SensorTable", header_row=True, borders_innerH=True, borders_outerH=True,
                   borders_innerV=True, borders_outerV=True, resizable=True, policy=mvTable_SizingStretchProp):
            add_table_column(label="Sensor ID")
            add_table_column(label="Temp")
            add_table_column(label="Humidity")
            add_table_column(label="Timestamp")
            add_table_column(label="Average")
            add_table_column(label="Std Dev")
            add_table_column(label="Anomaly")

        # threshold slider and anomaly list
        add_slider_float(label="Anomaly Threshold", tag="AnomalyThreshold",
                         default_value=anomaly_threshold, min_value=0.0, max_value=100.0,
                         width=300)
        add_text("Anomalies:", tag="AnomaliesLabel")
        add_child_window(tag="AnomalyList", width=780, height=100)

        add_spacing(count=2)

        add_text("Drone Status:")
        add_progress_bar(tag="BatteryProgress", default_value=battery_level / 100.0, width=300)
        add_text("Normal Operation", tag="StatusText")

        add_button(label="Simulate Battery Drain", callback=simulate_battery_drain)
        add_spacer(height=10)

        add_child_window(tag="LogScroll", width=780, height=200)
