import tkinter as tk
from tkinter import ttk
from datetime import datetime
import random
import src.drone.tcp_server as tcp_server
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg

# anomaly threshold and log
anomaly_threshold = 1.0
anomaly_log = []

battery_level = 100
sensor_data_log = []

# Global references to widgets for updating
sensor_table = None
anomaly_list_table = None
log_scroll_text = None
anomaly_threshold_scale = None
battery_progress = None
battery_label = None
status_text_label = None
avg_temp_fig = None
avg_temp_canvas = None
avg_humidity_fig = None
avg_humidity_canvas = None
ax_temp = None
ax_humidity = None

temperature_history = {}
humidity_history = {}

def update_sensor_data(sensor_data):
    """Append incoming sensor data, compute anomaly, and update GUI."""
    global sensor_data_log, anomaly_log, anomaly_list_table, avg_temp_canvas, avg_humidity_canvas, ax_temp, ax_humidity
    # Print sensor data for debugging
    print(sensor_data)

    # determine anomaly based on threshold or existing flag
    anomaly_flag = sensor_data.get("anomaly_flag", False)
    sensor_data_log.append(sensor_data)

    # add a new row to the sensor table
    values = (
        sensor_data["sensor_id"],
        str(sensor_data["temperature"]),
        str(sensor_data["humidity"]),
        str(sensor_data["timestamp"]),
        str(sensor_data.get("average", "")),
        str(sensor_data.get("std_dev", "")),
        "⚠" if anomaly_flag else ""
    )
    if sensor_table:
        sensor_table.insert("", "end", values=values)

    # logging panel
    log_msg = f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Data from {sensor_data['sensor_id']} received\n"
    if log_scroll_text:
        log_scroll_text.insert(tk.END, log_msg)
        log_scroll_text.see(tk.END)

    # if anomaly, add to anomaly list and anomaly table with type safety and error check
    if anomaly_flag and anomaly_list_table:
        try:
            sensor_id = str(sensor_data.get("sensor_id", ""))
            temp = float(sensor_data.get("temperature", 0.0))
            timestamp = str(sensor_data.get("timestamp", ""))
            print("✅ ANOMALY EKLENİYOR TABLOYA:", sensor_id, temp, timestamp)
            anomaly_list_table.insert("", "end", values=(sensor_id, temp, timestamp))
        except Exception as e:
            print("❌ Failed to insert into anomaly table:", e)

    # Update temperature and humidity history per sensor using average and humidity for graphs
    sensor_id = sensor_data["sensor_id"]
    # Use average if available, otherwise fall back to temperature
    temp_val = sensor_data.get("average", sensor_data["temperature"])
    hum_val = sensor_data.get("humidity")
    print("📈 TEMP_VAL:", temp_val, "HUM_VAL:", hum_val)

    # Safeguard: Only append if values exist and are not None
    if temp_val is not None and hum_val is not None:
        try:
            temp_val = float(temp_val)
            hum_val = float(hum_val)
            print("✅ Appending:", sensor_id, temp_val, hum_val)

            if sensor_id not in temperature_history:
                temperature_history[sensor_id] = []
            if sensor_id not in humidity_history:
                humidity_history[sensor_id] = []

            temperature_history[sensor_id].append(temp_val)
            humidity_history[sensor_id].append(hum_val)

            print("🧊 TEMP HISTORY:", temperature_history[sensor_id])
            print("💧 HUMIDITY HISTORY:", humidity_history[sensor_id])
        except Exception as e:
            print("❌ Cannot convert values to float:", temp_val, hum_val, e)

        # Limit history to last 30 entries
        if len(temperature_history[sensor_id]) > 30:
            temperature_history[sensor_id] = temperature_history[sensor_id][-30:]
        if len(humidity_history[sensor_id]) > 30:
            humidity_history[sensor_id] = humidity_history[sensor_id][-30:]

    # Clear and re-plot average temperature graph
    ax_temp.clear()
    ax_temp.set_title("Temperature (°C)")
    ax_temp.set_xlabel("Time (s)")
    ax_temp.set_ylabel("Temperature (°C)")
    markers = ['o', 's', '^', 'D', 'v', 'P', '*', 'X']
    for idx, (sid, temps) in enumerate(temperature_history.items()):
        if temps:
            ax_temp.set_xlim(-len(temps)+1, 0)
            ax_temp.set_ylim(0, 50)
            x_vals = list(range(-len(temps)+1, 1))
            marker = markers[idx % len(markers)]
            ax_temp.plot(x_vals, temps, label=sid, marker=marker)
            print(f"📊 PLOTTING TEMP for {sid}: {temps}")

    ax_temp.legend(loc='upper right')
    avg_temp_canvas.draw()

    # Clear and re-plot average humidity graph
    ax_humidity.clear()
    ax_humidity.set_title("Humidity (%)")
    ax_humidity.set_xlabel("Time (s)")
    ax_humidity.set_ylabel("Humidity (%)")
    for idx, (sid, hums) in enumerate(humidity_history.items()):
        if hums:
            ax_humidity.set_xlim(-len(hums)+1, 0)
            ax_humidity.set_ylim(0, 100)
            x_vals = list(range(-len(hums)+1, 1))
            marker = markers[idx % len(markers)]
            ax_humidity.plot(x_vals, hums, label=sid, marker=marker)
            print(f"📊 PLOTTING HUMIDITY for {sid}: {hums}")

    ax_humidity.legend(loc='upper right')
    avg_humidity_canvas.draw()

def build_drone_panel(root):
    global sensor_table, anomaly_list_table, log_scroll_text, anomaly_threshold_scale, avg_temp_fig, avg_temp_canvas, avg_humidity_fig, avg_humidity_canvas, ax_temp, ax_humidity, drain_button

    main_frame = tk.Frame(root, borderwidth=2, relief="groove")
    main_frame.pack(fill=tk.BOTH, expand=True)

    main_label = tk.Label(main_frame, text="Drone Edge GUI", font=("Arial", 14))
    main_label.pack(pady=5)

    # Top graph frame for average temperature and humidity
    top_graph_frame = tk.Frame(main_frame)
    top_graph_frame.pack(fill=tk.X, padx=5, pady= 15)

    # Average Temperature plot
    avg_temp_fig = plt.Figure(figsize=(7,3), dpi=100)
    ax_temp = avg_temp_fig.add_subplot(111)
    ax_temp.set_title("Average Temperature Over Time")
    ax_temp.set_xlabel("Time")
    ax_temp.set_ylabel("Avg Temp")
    ax_temp.set_xlim(0, 20)
    ax_temp.set_ylim(0, 50)
    avg_temp_canvas = FigureCanvasTkAgg(avg_temp_fig, master=top_graph_frame)
    avg_temp_canvas.get_tk_widget().pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

    # Average Humidity plot
    avg_humidity_fig = plt.Figure(figsize=(7,3), dpi=100)
    ax_humidity = avg_humidity_fig.add_subplot(111)
    ax_humidity.set_title("Average Humidity Over Time")
    ax_humidity.set_xlabel("Time")
    ax_humidity.set_ylabel("Avg Humidity")
    ax_humidity.set_xlim(0, 20)
    ax_humidity.set_ylim(0, 100)
    avg_humidity_canvas = FigureCanvasTkAgg(avg_humidity_fig, master=top_graph_frame)
    avg_humidity_canvas.get_tk_widget().pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

    

   

    # Simulate Battery Drain Button
    def simulate_battery_drain():
        tcp_server.battery_monitor.simulate_drain(10)

    drain_button = tk.Button(main_frame, text="Simulate Battery Drain", command=simulate_battery_drain)
    drain_button.pack(pady=5)


    # Battery Display Frame
    battery_frame = tk.Frame(main_frame)
    battery_frame.pack(pady=3)

    # Global tanım için referansı yukarıda yapmalısın: global battery_label
    global battery_label
    battery_label = tk.Label(battery_frame, text="Battery: 100%", font=("Arial", 10))
    battery_label.pack()

    # Battery güncelleme fonksiyonu
    def update_battery_display(level):
        if battery_label:
            battery_label.config(text=f"Battery: {level}%")

    # GUI'ye battery callback'ini tanıt
    from src.drone.battery_monitor import set_battery_callback
    set_battery_callback(update_battery_display)
  


    
   

   
