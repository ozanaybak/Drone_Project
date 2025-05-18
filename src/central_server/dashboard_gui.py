import tkinter as tk
from tkinter import ttk
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import matplotlib.pyplot as plt

buffer_data = []
sensor_selector = None
log_table = None
anomaly_log = None
fig = None
ax = None
line = None
canvas = None

def build_dashboard_panel(root):
    """
    Builds the central server dashboard GUI using tkinter,
    with two side-by-side panels:
      - Left panel: sensor selector, data table
      - Right panel: rolling line chart of temperature over time
    Returns (update_dashboard, clear_dashboard) callbacks.
    """
    global sensor_selector, log_table, anomaly_log, fig, ax, line, canvas, buffer_data

    buffer_data = []

    # Main container frames
    left_panel = tk.Frame(root, width=400)
    left_panel.pack(side=tk.LEFT, fill=tk.Y, padx=5, pady=5)

    right_panel = tk.Frame(root)
    right_panel.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=5, pady=5)

    # Left panel widgets
    tk.Label(left_panel, text="Select Sensor:").pack(anchor='w')

    sensor_selector = ttk.Combobox(left_panel, values=[])
    sensor_selector.pack(fill=tk.X)

    ttk.Separator(left_panel, orient='horizontal').pack(fill=tk.X, pady=5)

    tk.Label(left_panel, text="Anomalies:").pack(anchor='w')
    anomaly_log = ttk.Treeview(left_panel, columns=("Sensor ID", "Temp", "Timestamp"), show='headings', height=5)
    for col in ("Sensor ID", "Temp", "Timestamp"):
        anomaly_log.heading(col, text=col)
        anomaly_log.column(col, anchor='center')
    anomaly_log.pack(fill=tk.X, expand=False, padx=5, pady=(0, 5))

    ttk.Separator(left_panel, orient='horizontal').pack(fill=tk.X, pady=5)

    # Log table
    columns = ("Sensor ID", "Temp", "Humidity", "Timestamp")
    log_table = ttk.Treeview(left_panel, columns=columns, show='headings', height=8)
    for col in columns:
        log_table.heading(col, text=col)
        log_table.column(col, anchor='center')
    log_table.pack(fill=tk.BOTH, expand=True, padx=5)

    ttk.Separator(left_panel, orient='horizontal').pack(fill=tk.X, pady=5)

    # Right panel widgets - matplotlib plot
    fig, ax = plt.subplots(figsize=(6,4))
    ax.set_xlabel("Reading #")
    ax.set_ylabel("Temperature")
    line, = ax.plot([], [], 'b-')
    ax.set_xlim(0, 60)
    ax.set_ylim(0, 120)
    ax.grid(True)

    canvas = FigureCanvasTkAgg(fig, master=right_panel)
    canvas.draw()
    canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)

    def update_dashboard(sensor_data):
        selected = sensor_selector.get()
        if selected and sensor_data["sensor_id"] != selected:
            return
        buffer_data.append(sensor_data)
        if len(buffer_data) > 50:
            buffer_data.pop(0)

        # Update sensor selector values if needed
        sensor_ids = sorted(set(entry["sensor_id"] for entry in buffer_data))
        current_values = sensor_selector['values']
        if tuple(sensor_ids) != current_values:
            sensor_selector['values'] = sensor_ids
            if selected not in sensor_ids:
                sensor_selector.set('')

        # Update table rows
        for row in log_table.get_children():
            log_table.delete(row)
        for entry in buffer_data:
            log_table.insert('', 'end', values=(
                entry["sensor_id"],
                f"{entry['temperature']:.2f}",
                f"{entry['humidity']:.2f}",
                entry["timestamp"]
            ))

        if sensor_data.get("anomaly_flag"):
            anomaly_log.insert('', 'end', values=(
                sensor_data["sensor_id"],
                f"{sensor_data['temperature']:.2f}",
                sensor_data["timestamp"]
            ))

        # Update plot series
        indices = list(range(len(buffer_data)))
        temps = [e["temperature"] for e in buffer_data]
        line.set_data(indices, temps)
        ax.set_xlim(0, max(60, len(buffer_data)))
        if temps:
            ymin = min(temps) - 5
            ymax = max(temps) + 5
            ax.set_ylim(ymin if ymin < ymax else 0, ymax)
        else:
            ax.set_ylim(0, 120)
        canvas.draw_idle()

    def clear_dashboard():
        buffer_data.clear()
        # Clear table
        for row in log_table.get_children():
            log_table.delete(row)
        # Clear anomaly table
        for row in anomaly_log.get_children():
            anomaly_log.delete(row)
        # Clear plot
        line.set_data([], [])
        ax.set_xlim(0, 60)
        ax.set_ylim(0, 120)
        canvas.draw_idle()
        # Clear sensor selector
        sensor_selector.set('')
        sensor_selector['values'] = []

    return update_dashboard, clear_dashboard