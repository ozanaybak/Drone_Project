from dearpygui.dearpygui import *
from datetime import datetime

buffer_data = []

def update_dashboard(sensor_data):
    buffer_data.append(sensor_data)
    if len(buffer_data) > 5:
        buffer_data.pop(0)

    delete_item("LogTable", children_only=True)
    for entry in buffer_data:
        with table_row(parent="LogTable"):
            add_text(entry["sensor_id"])
            add_text(str(entry["temperature"]))
            add_text(str(entry["humidity"]))
            add_text(str(entry["timestamp"]))
            if entry.get("anomaly_flag"):
                log_message = f"[{entry['sensor_id']}] 🚨 Anomaly Detected!"
                add_text(log_message, parent="LogScroll")

def clear_dashboard_table(sender, app_data, user_data):
    global buffer_data
    buffer_data.clear()
    delete_item("LogTable", children_only=True)

def build_gui():
    with window(label="Central Server Dashboard", width=800, height=600):
        add_text("Central Dashboard Running", tag="StatusText")
        add_table("LogTable", ["Sensor ID", "Temp", "Humidity", "Timestamp"], height=200)
        add_spacing(count=2)
        add_text("Logs:")
        add_child("LogScroll", width=780, height=200)
        with child(label="Dashboard Panel", width=530, height=650, border=True):
            add_text("Central Server Dashboard", color=(200, 200, 255))
            add_button(label="Clear Dashboard", callback=clear_dashboard_table)
            add_separator()
            add_text("Server Log:", tag="ServerLogLabel")
            add_child_window(tag="CentralLog", width=-1, height=200)

start_dearpygui()