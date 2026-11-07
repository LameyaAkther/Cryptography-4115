import tkinter as tk

from tkinter import ttk, messagebox, filedialog

from pathlib import Path

import subprocess

import threading

import queue

import time

import re

import json

import csv

# ============================================================
# CONFIGURATION
# ============================================================

ROOT = Path(__file__).resolve().parent.parent

SERVER_EXE = ROOT / "server.exe"

CLIENT_EXE = ROOT / "client.exe"

BG = "#101827"

PANEL = "#1B2638"

CARD_BG = "#1E293B"

LAYER_BG = "#263449"

TEXT = "#E2E8F0"

BLUE = "#2563EB"

GREEN = "#16A34A"

WHITE = "#F8FAFC"

GRAY = "#94A3B8"

RED = "#EF4444"

DARK = "#0B1220"

CYAN = "#38BDF8"

PURPLE = "#C084FC"

ORANGE = "#F59E0B"

LAYERS = [

    "7. Application",

    "6. Presentation",

    "5. Session",

    "4. Transport",

    "3. Network",

    "2. Data Link",

    "1. Physical"

]

LAYER_INFO = {

    7: {

        "name": "Application",

        "pdu": "Data",

        "function": "Provides network services directly to user applications. It is the interface between the application and the network.",

        "protocols": "HTTP/HTTPS, DNS, SMTP, FTP",

        "header": "Application data / message",

        "example": "A browser creates an HTTP request when you open a website."

    },

    6: {

        "name": "Presentation",

        "pdu": "Data",

        "function": "Handles data translation, formatting, encryption/decryption and compression.",

        "protocols": "TLS/SSL, JPEG, PNG, ASCII, UTF-8",

        "header": "L6| (simulated)",

        "example": "Data may be encrypted or converted into a standard format."

    },

    5: {

        "name": "Session",

        "pdu": "Data",

        "function": "Establishes, manages and terminates communication sessions between applications.",

        "protocols": "RPC, NetBIOS, SIP (session concepts)",

        "header": "L5|SESSION_1001| (simulated)",

        "example": "Maintains a logical session while two applications communicate."

    },

    4: {

        "name": "Transport",

        "pdu": "Segment (TCP) / Datagram (UDP)",

        "function": "Provides end-to-end delivery, segmentation, reliability, flow control and port-based multiplexing.",

        "protocols": "TCP, UDP",

        "header": "L4|TCP| (simulated)",

        "example": "TCP helps deliver data reliably and in order."

    },

    3: {

        "name": "Network",

        "pdu": "Packet",

        "function": "Provides logical addressing and routing so packets can travel between networks.",

        "protocols": "IPv4, IPv6, ICMP",

        "header": "L3|127.0.0.1| (simulated)",

        "example": "IP addressing identifies the source and destination network hosts."

    },

    2: {

        "name": "Data Link",

        "pdu": "Frame",

        "function": "Handles node-to-node delivery, framing, MAC addressing and error detection on a local link.",

        "protocols": "Ethernet (IEEE 802.3), Wi-Fi MAC (IEEE 802.11)",

        "header": "L2|FRAME| (simulated)",

        "example": "Ethernet frames carry data across a local network segment."

    },

    1: {

        "name": "Physical",

        "pdu": "Bits",

        "function": "Transmits raw bits as electrical, optical or radio signals through a physical medium.",

        "protocols": "Ethernet PHY, Wi-Fi PHY, USB, DSL",

        "header": "No simulated text header",

        "example": "Actual hardware sends signals over cable, fiber or radio. This project models this layer conceptually."

    }

}

PACKET_PREFIXES = [

    ("Data Link", "L2|FRAME|"),

    ("Network", "L3|127.0.0.1|"),

    ("Transport", "L4|TCP|"),

    ("Session", "L5|SESSION_1001|"),

    ("Presentation", "L6|"),

]
# ============================================================
# APPLICATION STATE
# ============================================================

root = tk.Tk()

root.title("OSI Network Simulator - Advanced Edition")

root.geometry("1360x850")

root.minsize(1100, 700)

root.configure(bg=BG)

events = queue.Queue()

animation_queue = queue.Queue()

running = False

animation_active = False

current_layer = None

metric_labels = {}

metrics = {

    "PACKET_BYTES": "--",

    "ENCAPSULATION_MS": "--",

    "RTT_MS": "--",

    "TOTAL_CLIENT_MS": "--",

}

layer_frames = []

layer_labels = []

flow_items = {}

flow_positions = {}

flow_dot = None

# Stage 5: Performance history

performance_history = []

HISTORY_FILE = ROOT / "performance_history.json"

# ============================================================
# GENERAL HELPERS
# ============================================================

def write_log(message):

    if message.startswith("[ERROR]"):

        tag = "error"

    elif re.search(r"\[L[1-7]\s-", message):

        tag = "layer"

    elif message.startswith("METRIC|"):

        tag = "metric"

    elif "[CLIENT]" in message:

        tag = "client"

    elif "[SERVER]" in message:

        tag = "server"

    else:

        tag = "system"

    log.insert("end", message + "\n", tag)

    log.see("end")


def reset_layers():

    global current_layer

    current_layer = None

    for frame, label in zip(layer_frames, layer_labels):

        frame.configure(bg=LAYER_BG)

        label.configure(bg=LAYER_BG)


def highlight_layer(number):

    global current_layer

    reset_layers()

    index = 7 - number

    if 0 <= index < len(layer_frames):

        layer_frames[index].configure(bg=BLUE)

        layer_labels[index].configure(bg=BLUE)

        current_layer = number

    show_layer_details(number)

    highlight_flow_layer(number)


def show_layer_details(number):

    info = LAYER_INFO[number]

    layer_info_text.configure(state="normal")

    layer_info_text.delete("1.0", "end")

    layer_info_text.insert(

        "end",

        f"OSI Layer: {number} - {info['name']}\n\n"

    )

    layer_info_text.insert(

        "end",

        f"Main Function\n{info['function']}\n\n"

    )

    layer_info_text.insert(

        "end",

        f"PDU\n{info['pdu']}\n\n"

    )

    layer_info_text.insert(

        "end",

        f"Common Protocols / Standards\n{info['protocols']}\n\n"

    )

    layer_info_text.insert(

        "end",

        f"Project Header Representation\n{info['header']}\n\n"

    )

    layer_info_text.insert(

        "end",

        f"Example\n{info['example']}\n\n"

    )

    layer_info_text.insert(

        "end",

        "Note: OSI is a conceptual reference model. Some real-world "

        "protocols span multiple layers, and the headers shown here "

        "are educational simulations rather than actual wire-format "

        "protocol headers."

    )

    layer_info_text.configure(state="disabled")


def update_metric(key, value):

    if key not in metric_labels:

        return

    metrics[key] = value

    label, unit = metric_labels[key]

    try:

        if key == "PACKET_BYTES":

            formatted = f"{int(float(value)):,} {unit}"

        else:

            formatted = f"{float(value):.4f} {unit}"

    except (ValueError, TypeError):

        formatted = f"{value} {unit}"

    label.configure(text=formatted)


def reset_metrics():

    for key, (label, unit) in metric_labels.items():

        label.configure(text=f"-- {unit}")

        metrics[key] = "--"
        # ============================================================
# STAGE 5: PERFORMANCE HISTORY
# ============================================================

def save_history_to_json():

    """Save successful simulation records in the project root."""

    try:

        with open(HISTORY_FILE, "w", encoding="utf-8") as file:

            json.dump(performance_history, file, indent=4)

    except (OSError, TypeError) as error:

        write_log(f"[ERROR] Could not save history: {error}")


def load_history_from_json():

    """Restore valid previous simulation records when the GUI starts."""

    global performance_history

    if not HISTORY_FILE.exists():

        performance_history = []

        return

    try:

        with open(HISTORY_FILE, "r", encoding="utf-8") as file:

            loaded = json.load(file)

        if not isinstance(loaded, list):

            raise ValueError("History JSON must contain a list.")

        required = {

            "simulation", "PACKET_BYTES", "ENCAPSULATION_MS",

            "RTT_MS", "TOTAL_CLIENT_MS"

        }

        valid_records = []

        for item in loaded:

            if not isinstance(item, dict) or not required.issubset(item):

                continue

            try:

                valid_records.append({

                    "simulation": int(item["simulation"]),

                    "PACKET_BYTES": float(item["PACKET_BYTES"]),

                    "ENCAPSULATION_MS": float(item["ENCAPSULATION_MS"]),

                    "RTT_MS": float(item["RTT_MS"]),

                    "TOTAL_CLIENT_MS": float(item["TOTAL_CLIENT_MS"])

                })

            except (TypeError, ValueError):

                continue

        performance_history = valid_records

        update_history_table()

        draw_performance_graphs()

        write_log(

            f"[SYSTEM] Loaded {len(performance_history)} previous simulations."

        )

    except (OSError, json.JSONDecodeError, ValueError) as error:

        performance_history = []

        write_log(f"[ERROR] Could not load history: {error}")


def export_history_to_csv():

    if not performance_history:

        messagebox.showwarning(

            "No Data", "There is no performance history to export."

        )

        return

    path = filedialog.asksaveasfilename(

        title="Export Performance History",

        defaultextension=".csv",

        filetypes=[("CSV Files", "*.csv"), ("All Files", "*.*")],

        initialfile="osi_performance_history.csv"

    )

    if not path:

        return

    fields = [

        "simulation", "PACKET_BYTES", "ENCAPSULATION_MS",

        "RTT_MS", "TOTAL_CLIENT_MS"

    ]

    try:

        with open(path, "w", newline="", encoding="utf-8-sig") as file:

            writer = csv.DictWriter(file, fieldnames=fields)

            writer.writeheader()

            writer.writerows(performance_history)

        messagebox.showinfo("Export Successful", f"CSV exported to:\n{path}")

    except OSError as error:

        messagebox.showerror("Export Failed", str(error))


def export_history_to_json():

    if not performance_history:

        messagebox.showwarning(

            "No Data", "There is no performance history to export."

        )

        return

    path = filedialog.asksaveasfilename(

        title="Export Performance History",

        defaultextension=".json",

        filetypes=[("JSON Files", "*.json"), ("All Files", "*.*")],

        initialfile="osi_performance_history.json"

    )

    if not path:

        return

    try:

        with open(path, "w", encoding="utf-8") as file:

            json.dump(performance_history, file, indent=4)

        messagebox.showinfo("Export Successful", f"JSON exported to:\n{path}")

    except OSError as error:

        messagebox.showerror("Export Failed", str(error))


def show_performance_summary():

    if not performance_history:

        messagebox.showinfo(

            "Performance Summary", "Run at least one simulation first."

        )

        return

    count = len(performance_history)

    avg_rtt = sum(x["RTT_MS"] for x in performance_history) / count

    avg_enc = sum(x["ENCAPSULATION_MS"] for x in performance_history) / count

    avg_size = sum(x["PACKET_BYTES"] for x in performance_history) / count

    best = min(performance_history, key=lambda x: x["RTT_MS"])

    summary = (

        f"TOTAL SIMULATIONS: {count}\n\n"

        f"AVERAGE RTT: {avg_rtt:.4f} ms\n\n"

        f"AVERAGE ENCAPSULATION TIME: {avg_enc:.4f} ms\n\n"

        f"AVERAGE PACKET SIZE: {avg_size:.2f} bytes\n\n"

        f"BEST RTT: Run {best['simulation']} "

        f"({best['RTT_MS']:.4f} ms)"

    )

    messagebox.showinfo("Performance Summary", summary)
def save_performance_history():

    required_metrics = [
        "PACKET_BYTES",
        "ENCAPSULATION_MS",
        "RTT_MS",
        "TOTAL_CLIENT_MS"
    ]

    record = {}

    for key in required_metrics:

        try:
            record[key] = float(metrics[key])

        except (ValueError, TypeError):

            write_log(
                f"[ERROR] Missing or invalid metric: {key}"
            )

            return

    record["simulation"] = len(performance_history) + 1

    performance_history.append(record)

    save_history_to_json()

    write_log(
        f"[SYSTEM] Performance data saved for Run "
        f"{record['simulation']}."
    )

    draw_performance_graphs()

    update_history_table()


def clear_performance_history():

    if not performance_history:

        messagebox.showinfo(

            "Performance History",

            "There is no saved performance history."

        )

        return

    confirm = messagebox.askyesno(

        "Clear Performance History",

        "Are you sure you want to delete all saved simulation results?"

    )

    if not confirm:

        return

    performance_history.clear()

    save_history_to_json()

    draw_performance_graphs()

    update_history_table()

    write_log("[SYSTEM] Performance history cleared.")


def update_history_table():

    history_tree.delete(

        *history_tree.get_children()

    )

    for record in performance_history:

        history_tree.insert(

            "",

            "end",

            values=(

                record["simulation"],

                f"{record['PACKET_BYTES']:.0f}",

                f"{record['ENCAPSULATION_MS']:.4f}",

                f"{record['RTT_MS']:.4f}",

                f"{record['TOTAL_CLIENT_MS']:.4f}"

            )

        )


def draw_metric_chart(canvas, metric_key, title, unit):

    canvas.delete("all")

    width = max(canvas.winfo_width(), 350)

    height = max(canvas.winfo_height(), 220)

    left = 55

    right = width - 25

    top = 48

    bottom = height - 42

    canvas.create_text(

        width / 2,

        20,

        text=title,

        fill=WHITE,

        font=("Segoe UI", 11, "bold")

    )

    if not performance_history:

        canvas.create_text(

            width / 2,

            height / 2,

            text="Run simulations to generate performance data",

            fill=GRAY,

            font=("Segoe UI", 9)

        )

        return

    records = performance_history[-10:]

    values = [

        record[metric_key]

        for record in records

    ]

    max_value = max(values)

    if max_value <= 0:

        max_value = 1

    chart_width = right - left

    chart_height = bottom - top

    # Y-axis and X-axis

    canvas.create_line(

        left, top,

        left, bottom,

        fill=GRAY

    )

    canvas.create_line(

        left, bottom,

        right, bottom,

        fill=GRAY

    )

    # Horizontal grid lines

    for i in range(5):

        y = top + i * chart_height / 4

        canvas.create_line(

            left,

            y,

            right,

            y,

            fill="#334155",

            dash=(2, 4)

        )

        axis_value = max_value * (4 - i) / 4

        canvas.create_text(

            left - 7,

            y,

            anchor="e",

            text=f"{axis_value:.1f}",

            fill=GRAY,

            font=("Segoe UI", 7)

        )

    count = len(records)

    slot_width = chart_width / count

    bar_width = min(35, slot_width * 0.55)

    for index, record in enumerate(records):

        value = record[metric_key]

        bar_height = (

            value / max_value

        ) * chart_height

        center_x = (

            left + index * slot_width + slot_width / 2

        )

        x1 = center_x - bar_width / 2

        x2 = center_x + bar_width / 2

        y1 = bottom - bar_height

        canvas.create_rectangle(

            x1,

            y1,

            x2,

            bottom,

            fill=BLUE,

            outline=CYAN,

            width=1

        )

        canvas.create_text(

            center_x,

            max(top + 10, y1 - 12),

            text=f"{value:.2f}",

            fill=WHITE,

            font=("Segoe UI", 8)

        )

        canvas.create_text(

            center_x,

            bottom + 17,

            text=f"Run {record['simulation']}",

            fill=GRAY,

            font=("Segoe UI", 8)

        )


def draw_performance_graphs():

    if "rtt_canvas" not in globals():

        return

    draw_metric_chart(

        rtt_canvas,

        "RTT_MS",

        "TCP ROUND-TRIP TIME",

        "ms"

    )

    draw_metric_chart(

        encapsulation_canvas,

        "ENCAPSULATION_MS",

        "ENCAPSULATION TIME",

        "ms"

    )

    draw_metric_chart(

        packet_size_canvas,

        "PACKET_BYTES",

        "PACKET SIZE",

        "bytes"

    )
    # PACKET + HEADER INSPECTOR

# ============================================================

def show_packet(packet):

    packet_view.delete("1.0", "end")

    structure_view.delete("1.0", "end")

    header_tree.delete(
        *header_tree.get_children()
    )

    packet_view.insert("end", packet)

    remaining = packet

    structure_view.insert(
        "end",
        "[Physical] TCP socket transmission bytes\n"
    )

    header_rows = []

    for layer_name, prefix in PACKET_PREFIXES:

        if remaining.startswith(prefix):

            header_rows.append(
                (layer_name, prefix, "Found")
            )

            structure_view.insert(
                "end",
                f"[{layer_name}] Header: {prefix}\n"
            )

            remaining = remaining[len(prefix):]

        else:

            header_rows.append(
                (layer_name, "(not present at this position)", "Not found")
            )

            structure_view.insert(
                "end",
                f"[{layer_name}] Header not found\n"
            )

            break

    structure_view.insert(
        "end",
        "\n[Application Payload]\n" + remaining
    )

    structure_view.insert(
        "end",
        "\n\nNote: These are simulated educational headers, "
        "not real Ethernet/IP/TCP bytes."
    )

    for name, header, state in header_rows:

        header_tree.insert(
            "",
            "end",
            values=(name, header, state)
        )

    header_tree.insert(
        "",
        "end",
        values=("Application Payload", remaining, "Payload")
    )

    notebook.select(packet_tab)
  # ============================================================

# GRAPHICAL PACKET FLOW

# ============================================================

def draw_packet_flow():

    global flow_dot

    flow_canvas.delete("all")

    flow_items.clear()

    flow_positions.clear()

    width = max(flow_canvas.winfo_width(), 600)

    height = max(flow_canvas.winfo_height(), 360)

    x1 = 70

    x2 = width - 70

    y_top = 32

    box_height = 24

    gap = 26

    flow_canvas.create_text(
        width / 2,
        16,
        text="CLIENT ENCAPSULATION  →  SERVER DECAPSULATION",
        fill=CYAN,
        font=("Segoe UI", 10, "bold")
    )

    for number in range(7, 0, -1):

        y = y_top + (7 - number) * gap

        flow_positions[number] = (
            x1, y, x2, y + box_height
        )

        flow_canvas.create_line(
            x1 + 100,
            y + box_height / 2,
            x2 - 100,
            y + box_height / 2,
            fill="#475569",
            dash=(4, 4),
            width=2
        )

        rect = flow_canvas.create_rectangle(
            x1,
            y,
            x2,
            y + box_height,
            fill=LAYER_BG,
            outline="#475569",
            width=1
        )

        label = flow_canvas.create_text(
            x1 + 12,
            y + box_height / 2,
            anchor="w",
            text=f"L{number}  {LAYER_INFO[number]['name']}",
            fill=WHITE,
            font=("Segoe UI", 9, "bold")
        )

        state = flow_canvas.create_text(
            x2 - 12,
            y + box_height / 2,
            anchor="e",
            text="WAITING",
            fill=GRAY,
            font=("Consolas", 8)
        )

        flow_items[number] = (
            rect,
            label,
            state
        )

    flow_canvas.create_text(
        25,
        height - 15,
        anchor="w",
        text="CLIENT",
        fill=GREEN,
        font=("Segoe UI", 9, "bold")
    )

    flow_canvas.create_text(
        width - 25,
        height - 15,
        anchor="e",
        text="SERVER",
        fill=ORANGE,
        font=("Segoe UI", 9, "bold")
    )

    flow_dot = flow_canvas.create_oval(
        x1 + 8,
        y_top + 6,
        x1 + 22,
        y_top + 20,
        fill=CYAN,
        outline=WHITE,
        width=1
    )


def highlight_flow_layer(number):

    if number not in flow_items:

        return

    for n, (rect, label, state) in flow_items.items():

        if n == number:

            flow_canvas.itemconfigure(
                rect,
                fill=BLUE,
                outline=CYAN,
                width=2
            )

            flow_canvas.itemconfigure(
                state,
                text="ACTIVE",
                fill=CYAN
            )

        else:

            flow_canvas.itemconfigure(
                rect,
                fill=LAYER_BG,
                outline="#475569",
                width=1
            )

            if flow_canvas.itemcget(state, "text") == "ACTIVE":

                flow_canvas.itemconfigure(
                    state,
                    text="PROCESSED",
                    fill=GREEN
                )  
def move_flow_dot(number, source):

    if flow_dot is None or number not in flow_positions:

        return

    x1, y1, x2, y2 = flow_positions[number]

    cy = (y1 + y2) / 2

    if source == "server":

        start_x = x2 - 24

        end_x = x1 + 24

    else:

        start_x = x1 + 24

        end_x = x2 - 24

    flow_canvas.coords(

        flow_dot,

        start_x - 7,

        cy - 7,

        start_x + 7,

        cy + 7

    )

    steps = 18

    def animate(step=0):

        if step > steps:

            return

        x = start_x + (

            end_x - start_x

        ) * step / steps

        flow_canvas.coords(

            flow_dot,

            x - 7,

            cy - 7,

            x + 7,

            cy + 7

        )

        root.after(

            18,

            lambda: animate(step + 1)

        )

    animate()

    def animate(step=0):

        if step > steps:

            return

        x = start_x + (
            end_x - start_x
        ) * step / steps

        flow_canvas.coords(
            flow_dot,
            x - 7,
            cy - 7,
            x + 7,
            cy + 7
        )

        root.after(
            18,
            lambda: animate(step + 1)
        )

    animate()


# ============================================================

# REAL-TIME OSI ANIMATION

# ============================================================

def process_animation():

    global animation_active

    if animation_active:

        return

    try:

        source, message = animation_queue.get_nowait()

    except queue.Empty:

        return

    animation_active = True

    match = re.search(
        r"\[L([1-7])\s-\s([^\]]+)\]",
        message
    )

    if match:

        number = int(match.group(1))

        if source == "server":

            direction_label.configure(
                text="SERVER: DECAPSULATION"
            )

        else:

            direction_label.configure(
                text="CLIENT: ENCAPSULATION"
            )

        highlight_layer(number)

        move_flow_dot(number, source)

    prefix = (
        "[CLIENT]"
        if source == "client"
        else "[SERVER]"
    )

    write_log(f"{prefix} {message}")

    def finish_animation():

        global animation_active

        animation_active = False

        if not animation_queue.empty():

            root.after(
                80,
                process_animation
            )

    root.after(
        220,
        finish_animation
    )
    # ============================================================
# PROCESS OUTPUT HANDLER
# ============================================================

def handle_output(source, line):

    line = line.rstrip("\r\n")

    if not line:

        return

    # PACKET INSPECTOR

    if line.startswith("PACKET|"):

        packet = line[len("PACKET|"):]

        root.after(

            0,

            lambda p=packet: show_packet(p)

        )

        return

    # PERFORMANCE METRICS

    if line.startswith("METRIC|"):

        parts = line.split("|", 2)

        if len(parts) == 3:

            key = parts[1].upper()

            value = parts[2]

            update_metric(key, value)

            write_log(line)

        return

    # OSI LAYER ANIMATION

    if re.search(r"\[L[1-7]\s-", line):

        animation_queue.put(

            (source, line)

        )

        root.after(

            0,

            process_animation

        )

        return

    # NORMAL OUTPUT

    root.after(

        0,

        lambda s=source, m=line:

        write_log(f"[{s.upper()}] {m}")

    )
 # ============================================================
# BACKGROUND PROCESS COMMUNICATION
# ============================================================

def read_process_output(process, source):

    try:

        if process.stdout is not None:

            for line in process.stdout:

                events.put(

                    (source, line)

                )

    finally:

        events.put(

            (source, "__OUTPUT_FINISHED__")

        )   
# ============================================================
# START SIMULATION
# ============================================================

def start_simulation():

    global running, animation_active

    if running:
        return

    message = message_entry.get().strip()

    if not message:
        messagebox.showwarning(
            "Message Required",
            "Please enter a message."
        )
        return

    if len(message.encode("utf-8")) >= 4000:
        messagebox.showwarning(
            "Message Too Large",
            "Please use a message shorter than 4000 bytes."
        )
        return

    if not SERVER_EXE.exists():
        messagebox.showerror(
            "Missing File",
            f"server.exe not found:\n{SERVER_EXE}"
        )
        return

    if not CLIENT_EXE.exists():
        messagebox.showerror(
            "Missing File",
            f"client.exe not found:\n{CLIENT_EXE}"
        )
        return

    running = True
    animation_active = False

    while not animation_queue.empty():
        try:
            animation_queue.get_nowait()
        except queue.Empty:
            break

    reset_layers()
    reset_metrics()

    log.delete("1.0", "end")
    packet_view.delete("1.0", "end")
    structure_view.delete("1.0", "end")

    header_tree.delete(
        *header_tree.get_children()
    )

    status.configure(
        text="● STARTING SIMULATION",
        fg=BLUE
    )

    connection.configure(
        text="SERVER: STARTING    CLIENT: WAITING",
        fg=BLUE
    )

    start_button.configure(state="disabled")
    reset_button.configure(state="disabled")

    notebook.select(activity_tab)

    write_log(
        "[SYSTEM] Starting OSI simulation..."
    )

    threading.Thread(
        target=communication_worker,
        args=(message,),
        daemon=True
    ).start()


# ============================================================
# RESET SIMULATION
# ============================================================

def reset_simulation():

    if running:
        return

    reset_layers()
    reset_metrics()

    log.delete("1.0", "end")
    packet_view.delete("1.0", "end")
    structure_view.delete("1.0", "end")

    header_tree.delete(
        *header_tree.get_children()
    )

    status.configure(
        text="● SYSTEM READY",
        fg=GREEN
    )

    connection.configure(
        text="SERVER: STOPPED    CLIENT: IDLE",
        fg=GRAY
    )

    direction_label.configure(
        text="WAITING FOR TRANSMISSION"
    )

    write_log("[SYSTEM] Simulator reset.")
def communication_worker(message):

    server = None
    client = None
    reader_threads = []
    error = None

    try:

        # START SERVER
        server = subprocess.Popen(
            [str(SERVER_EXE)],
            cwd=str(ROOT),
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            encoding="utf-8",
            errors="replace",
            bufsize=1
        )

        server_reader = threading.Thread(
            target=read_process_output,
            args=(server, "server"),
            daemon=True
        )

        server_reader.start()
        reader_threads.append(server_reader)

        # WAIT FOR SERVER
        time.sleep(0.8)

        if server.poll() is not None:
            raise RuntimeError(
                "Server stopped unexpectedly. "
                "Check server.exe and port 8080."
            )

        # START CLIENT
        client = subprocess.Popen(
            [str(CLIENT_EXE), message],
            cwd=str(ROOT),
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            encoding="utf-8",
            errors="replace",
            bufsize=1
        )

        client_reader = threading.Thread(
            target=read_process_output,
            args=(client, "client"),
            daemon=True
        )

        client_reader.start()
        reader_threads.append(client_reader)

        # WAIT FOR COMMUNICATION
        client_code = client.wait(timeout=30)
        server_code = server.wait(timeout=15)

        if client_code != 0:
            raise RuntimeError(
                f"Client exited with code {client_code}."
            )

        if server_code != 0:
            raise RuntimeError(
                f"Server exited with code {server_code}."
            )

    except subprocess.TimeoutExpired:
        error = (
            "Communication timed out. "
            "Check C client/server socket code."
        )

    except Exception as exc:
        error = str(exc)

    finally:

        for process in (client, server):

            if process is not None and process.poll() is None:

                process.kill()

                try:
                    process.wait(timeout=3)
                except subprocess.TimeoutExpired:
                    pass

        for reader in reader_threads:
            reader.join(timeout=3)

        events.put(
            ("system", ("DONE", error))
        )


# ============================================================
# QUEUE POLLING
# ============================================================

def poll_events():

    global running

    try:

        while True:

            source, data = events.get_nowait()

            if source == "system":

                if isinstance(data, tuple) and data[0] == "DONE":

                    error = data[1]

                    running = False

                    start_button.configure(state="normal")

                    reset_button.configure(state="normal")

                    if error:

                        status.configure(

                            text="● SIMULATION ERROR",

                            fg=RED

                        )

                        connection.configure(

                            text="SERVER: ERROR    CLIENT: STOPPED",

                            fg=RED

                        )

                        write_log(f"[ERROR] {error}")

                        messagebox.showerror(

                            "Simulation Error",

                            error

                        )

                    else:

                        status.configure(

                            text="● SIMULATION COMPLETED",

                            fg=GREEN

                        )

                        connection.configure(

                            text="SERVER: STOPPED    CLIENT: COMPLETED",

                            fg=GREEN

                        )

                        save_performance_history()

                        write_log(

                            "[SYSTEM] Simulation completed successfully."

                        )

                    continue

            if data == "__OUTPUT_FINISHED__":

                continue

            handle_output(source, data)

    except queue.Empty:

        pass

    root.after(50, poll_events)

# ============================================================
# QUEUE POLLING
# ============================================================

    # ============================================================

# STYLES

# ============================================================

style = ttk.Style()

style.theme_use("clam")

style.configure(

    "TNotebook",

    background=BG,

    borderwidth=0

)

style.configure(

    "TNotebook.Tab",

    background=LAYER_BG,

    foreground=TEXT,

    padding=(16, 9),

    font=("Segoe UI", 9, "bold")

)

style.map(

    "TNotebook.Tab",

    background=[

        ("selected", BLUE)

    ],

    foreground=[

        ("selected", WHITE)

    ]

)

style.configure(

    "Treeview",

    background=CARD_BG,

    foreground=TEXT,

    fieldbackground=CARD_BG,

    rowheight=30,

    borderwidth=0,

    font=("Segoe UI", 9)

)

style.configure(

    "Treeview.Heading",

    background=LAYER_BG,

    foreground=WHITE,

    font=("Segoe UI", 9, "bold"),

    relief="flat"

)

style.map(

    "Treeview",

    background=[

        ("selected", BLUE)

    ],

    foreground=[

        ("selected", WHITE)

    ]

)
# ============================================================

# HEADER

# ============================================================

header = tk.Frame(

    root,

    bg=PANEL,

    height=62

)

header.pack(

    fill="x",

    padx=12,

    pady=10

)

header.pack_propagate(False)

tk.Label(

    header,

    text="OSI NETWORK SIMULATOR",

    bg=PANEL,

    fg=WHITE,

    font=("Segoe UI", 20, "bold")

).pack(

    side="left",

    padx=20

)

tk.Label(

    header,

    text="ADVANCED TCP SOCKET MONITOR",

    bg=PANEL,

    fg=GREEN,

    font=("Segoe UI", 9, "bold")

).pack(

    side="right",

    padx=20

)

# ============================================================

# MAIN LAYOUT

# ============================================================

main = tk.Frame(

    root,

    bg=BG

)

main.pack(

    fill="both",

    expand=True,

    padx=12,

    pady=(0, 10)

)

# LEFT PANEL

left = tk.Frame(

    main,

    bg=PANEL,

    width=265

)

left.pack(

    side="left",

    fill="y",

    padx=(0, 9)

)

left.pack_propagate(False)

tk.Label(

    left,

    text="OSI 7 LAYER MODEL",

    bg=PANEL,

    fg=WHITE,

    font=("Segoe UI", 13, "bold")

).pack(

    pady=(16, 10)

)

for layer_name in LAYERS:

    number = int(layer_name.split(".")[0])

    frame = tk.Frame(

        left,

        bg=LAYER_BG,

        height=50,

        cursor="hand2"

    )

    frame.pack(

        fill="x",

        padx=12,

        pady=4

    )

    frame.pack_propagate(False)

    label = tk.Label(

        frame,

        text=layer_name,

        bg=LAYER_BG,

        fg=WHITE,

        font=("Segoe UI", 10, "bold"),

        cursor="hand2"

    )

    label.pack(

        expand=True,

        fill="both"

    )

    frame.bind(

        "<Button-1>",

        lambda event, n=number: highlight_layer(n)

    )

    label.bind(

        "<Button-1>",

        lambda event, n=number: highlight_layer(n)

    )

    layer_frames.append(frame)

    layer_labels.append(label)

direction_label = tk.Label(

    left,

    text="WAITING FOR TRANSMISSION",

    bg=PANEL,

    fg=GRAY,

    font=("Consolas", 8, "bold"),

    wraplength=230

)

direction_label.pack(pady=12)

left_hint = tk.Label(

    left,

    text="Tip: Click any layer to view its details.",

    bg=PANEL,

    fg=CYAN,

    font=("Segoe UI", 8),

    wraplength=225

)

left_hint.pack(pady=(4, 8))
# RIGHT PANEL

right = tk.Frame(

    main,

    bg=PANEL

)

right.pack(

    side="right",

    fill="both",

    expand=True

)

tk.Label(

    right,

    text="NETWORK MONITOR",

    bg=PANEL,

    fg=WHITE,

    font=("Segoe UI", 14, "bold")

).pack(pady=(10, 2))

status = tk.Label(

    right,

    text="● SYSTEM READY",

    bg=PANEL,

    fg=GREEN,

    font=("Segoe UI", 10, "bold")

)

status.pack(pady=2)

# ============================================================

# MESSAGE INPUT

# ============================================================

input_frame = tk.Frame(

    right,

    bg=PANEL

)

input_frame.pack(

    fill="x",

    padx=14,

    pady=(5, 4)

)

tk.Label(

    input_frame,

    text="APPLICATION MESSAGE",

    bg=PANEL,

    fg=GRAY,

    font=("Segoe UI", 8, "bold")

).pack(anchor="w")

message_entry = tk.Entry(

    input_frame,

    bg=LAYER_BG,

    fg=WHITE,

    insertbackground=WHITE,

    font=("Segoe UI", 10),

    relief="flat"

)

message_entry.pack(

    fill="x",

    ipady=8,

    pady=4

)

message_entry.insert(

    0,

    "Hello from OSI Simulator!"

)
# ============================================================

# CONNECTION STATUS AND CONTROLS

# ============================================================

connection = tk.Label(

    right,

    text="SERVER: STOPPED    CLIENT: IDLE",

    bg=PANEL,

    fg=GRAY,

    font=("Consolas", 8, "bold")

)

controls = tk.Frame(

    right,

    bg=PANEL

)

start_button = tk.Button(

    controls,

    text="START SIMULATION",

    command=start_simulation,

    bg=BLUE,

    fg=WHITE,

    activebackground="#1D4ED8",

    activeforeground=WHITE,

    font=("Segoe UI", 9, "bold"),

    relief="flat",

    padx=20,

    pady=9,

    cursor="hand2"

)

start_button.pack(

    side="left",

    padx=6

)

reset_button = tk.Button(

    controls,

    text="RESET",

    command=reset_simulation,

    bg="#334155",

    fg=WHITE,

    activebackground="#475569",

    activeforeground=WHITE,

    font=("Segoe UI", 9, "bold"),

    relief="flat",

    padx=20,

    pady=9,

    cursor="hand2"

)

reset_button.pack(

    side="left",

    padx=6

)

controls.pack(

    side="bottom",

    pady=(3, 7)

)

connection.pack(

    side="bottom",

    pady=(2, 4)

)
# ============================================================

# NOTEBOOK TABS

# ============================================================

notebook = ttk.Notebook(right)

notebook.pack(

    fill="both",

    expand=True,

    padx=10,

    pady=8

)

activity_tab = tk.Frame(

    notebook,

    bg=BG

)

packet_tab = tk.Frame(

    notebook,

    bg=BG

)

header_tab = tk.Frame(

    notebook,

    bg=BG

)

layer_tab = tk.Frame(

    notebook,

    bg=BG

)

flow_tab = tk.Frame(

    notebook,

    bg=BG

)

performance_tab = tk.Frame(

    notebook,

    bg=BG

)

notebook.add(

    activity_tab,

    text="Activity"

)

notebook.add(

    packet_tab,

    text="Packet Inspector"

)

notebook.add(

    header_tab,

    text="Header Inspector"

)

notebook.add(

    layer_tab,

    text="Layer Details"

)

notebook.add(

    flow_tab,

    text="Packet Flow"

)

notebook.add(

    performance_tab,

    text="Performance"

)

# ============================================================

# ACTIVITY MONITOR

# ============================================================

log = tk.Text(

    activity_tab,

    bg=DARK,

    fg="#22C55E",

    insertbackground=WHITE,

    font=("Consolas", 9),

    relief="flat",

    wrap="word",

    padx=10,

    pady=10

)

log.pack(

    fill="both",

    expand=True,

    padx=8,

    pady=8

)

log.tag_config("error", foreground=RED)

log.tag_config("layer", foreground=CYAN)

log.tag_config("system", foreground="#22C55E")

log.tag_config("metric", foreground=PURPLE)

log.tag_config("client", foreground="#A7F3D0")

log.tag_config("server", foreground="#93C5FD")
# ============================================================
# PACKET INSPECTOR TAB
# ============================================================

tk.Label(

    packet_tab,

    text="TRANSMITTED PACKET",

    bg=BG,

    fg=WHITE,

    font=("Segoe UI", 11, "bold")

).pack(

    anchor="w",

    padx=12,

    pady=(12, 5)

)

packet_view = tk.Text(

    packet_tab,

    bg=DARK,

    fg=CYAN,

    insertbackground=WHITE,

    font=("Consolas", 10),

    relief="flat",

    wrap="word",

    height=5

)

packet_view.pack(

    fill="x",

    padx=12,

    pady=5

)

tk.Label(

    packet_tab,

    text="PACKET STRUCTURE",

    bg=BG,

    fg=WHITE,

    font=("Segoe UI", 11, "bold")

).pack(

    anchor="w",

    padx=12,

    pady=(12, 5)

)

structure_view = tk.Text(

    packet_tab,

    bg=DARK,

    fg="#A7F3D0",

    insertbackground=WHITE,

    font=("Consolas", 9),

    relief="flat",

    wrap="word"

)

structure_view.pack(

    fill="both",

    expand=True,

    padx=12,

    pady=5

)

# ============================================================
# HEADER INSPECTOR TAB
# ============================================================

tk.Label(

    header_tab,

    text="SIMULATED ENCAPSULATION HEADERS",

    bg=BG,

    fg=WHITE,

    font=("Segoe UI", 11, "bold")

).pack(

    anchor="w",

    padx=12,

    pady=12

)

header_tree = ttk.Treeview(

    header_tab,

    columns=("layer", "header", "status"),

    show="headings"

)

header_tree.heading(

    "layer",

    text="OSI Layer"

)

header_tree.heading(

    "header",

    text="Header Representation"

)

header_tree.heading(

    "status",

    text="Status"

)

header_tree.column(

    "layer",

    width=140,

    anchor="w"

)

header_tree.column(

    "header",

    width=360,

    anchor="w"

)

header_tree.column(

    "status",

    width=100,

    anchor="center"

)

header_tree.pack(

    fill="both",

    expand=True,

    padx=12,

    pady=8

)
# ============================================================
# LAYER DETAILS TAB
# ============================================================

tk.Label(

    layer_tab,

    text="OSI LAYER INFORMATION",

    bg=BG,

    fg=WHITE,

    font=("Segoe UI", 11, "bold")

).pack(

    anchor="w",

    padx=12,

    pady=10

)

layer_info_text = tk.Text(

    layer_tab,

    bg=DARK,

    fg=TEXT,

    insertbackground=WHITE,

    font=("Segoe UI", 10),

    relief="flat",

    wrap="word",

    padx=14,

    pady=14

)

layer_info_text.pack(

    fill="both",

    expand=True,

    padx=12,

    pady=8

)

layer_info_text.configure(

    state="disabled"

)

# ============================================================
# PACKET FLOW TAB
# ============================================================

tk.Label(

    flow_tab,

    text="REAL-TIME PACKET JOURNEY",

    bg=BG,

    fg=WHITE,

    font=("Segoe UI", 11, "bold")

).pack(

    anchor="w",

    padx=12,

    pady=10

)

flow_canvas = tk.Canvas(

    flow_tab,

    bg=DARK,

    highlightthickness=0,

    height=360

)

flow_canvas.pack(

    fill="both",

    expand=True,

    padx=10,

    pady=8

)

flow_canvas.bind(

    "<Configure>",

    lambda event: draw_packet_flow()

)
# ============================================================
# PERFORMANCE DASHBOARD TAB
# ============================================================

tk.Label(

    performance_tab,

    text="SIMULATION PERFORMANCE METRICS",

    bg=BG,

    fg=WHITE,

    font=("Segoe UI", 12, "bold")

).pack(

    anchor="w",

    padx=12,

    pady=(12, 8)

)

metric_container = tk.Frame(

    performance_tab,

    bg=BG

)

metric_container.pack(

    fill="x",

    padx=8,

    pady=5

)

def create_metric_card(parent, title, key, unit):

    card = tk.Frame(

        parent,

        bg=CARD_BG,

        padx=12,

        pady=12

    )

    card.pack(

        side="left",

        fill="both",

        expand=True,

        padx=5

    )

    tk.Label(

        card,

        text=title,

        bg=CARD_BG,

        fg=GRAY,

        font=("Segoe UI", 8, "bold")

    ).pack()

    value_label = tk.Label(

        card,

        text=f"-- {unit}",

        bg=CARD_BG,

        fg=CYAN,

        font=("Segoe UI", 15, "bold")

    )

    value_label.pack(pady=(7, 0))

    metric_labels[key] = (

        value_label,

        unit

    )

    return card


create_metric_card(

    metric_container,

    "PACKET SIZE",

    "PACKET_BYTES",

    "bytes"

)

create_metric_card(

    metric_container,

    "ENCAPSULATION TIME",

    "ENCAPSULATION_MS",

    "ms"

)

create_metric_card(

    metric_container,

    "ROUND-TRIP TIME",

    "RTT_MS",

    "ms"

)

create_metric_card(

    metric_container,

    "TOTAL CLIENT TIME",

    "TOTAL_CLIENT_MS",

    "ms"

)

# ============================================================
# PERFORMANCE HISTORY BUTTONS
# ============================================================

history_toolbar = tk.Frame(

    performance_tab,

    bg=BG

)

history_toolbar.pack(

    fill="x",

    padx=12,

    pady=12

)

tk.Button(

    history_toolbar,

    text="VIEW HISTORY",

    command=lambda: open_history_window(),

    bg=BLUE,

    fg=WHITE,

    relief="flat",

    padx=12,

    pady=7,

    cursor="hand2"

).pack(side="left", padx=4)

tk.Button(

    history_toolbar,

    text="SUMMARY",

    command=show_performance_summary,

    bg="#334155",

    fg=WHITE,

    relief="flat",

    padx=12,

    pady=7,

    cursor="hand2"

).pack(side="left", padx=4)

tk.Button(

    history_toolbar,

    text="EXPORT CSV",

    command=export_history_to_csv,

    bg="#334155",

    fg=WHITE,

    relief="flat",

    padx=12,

    pady=7,

    cursor="hand2"

).pack(side="left", padx=4)

tk.Button(

    history_toolbar,

    text="EXPORT JSON",

    command=export_history_to_json,

    bg="#334155",

    fg=WHITE,

    relief="flat",

    padx=12,

    pady=7,

    cursor="hand2"

).pack(side="left", padx=4)

tk.Button(

    history_toolbar,

    text="CLEAR HISTORY",

    command=clear_performance_history,

    bg="#991B1B",

    fg=WHITE,

    relief="flat",

    padx=12,

    pady=7,

    cursor="hand2"

).pack(side="right", padx=4)

# ============================================================
# SEPARATE PERFORMANCE GRAPHS TAB
# ============================================================

graphs_tab = tk.Frame(

    notebook,

    bg=BG

)

notebook.add(

    graphs_tab,

    text="Performance Graphs"

)


# ============================================================
# SCROLLABLE PERFORMANCE GRAPHS
# ============================================================

graphs_tab.columnconfigure(0, weight=1)
graphs_tab.rowconfigure(0, weight=1)

# Main scrollable canvas
graphs_scroll_canvas = tk.Canvas(
    graphs_tab,
    bg=BG,
    highlightthickness=0
)

graphs_scrollbar = ttk.Scrollbar(
    graphs_tab,
    orient="vertical",
    command=graphs_scroll_canvas.yview
)

graphs_scroll_canvas.configure(
    yscrollcommand=graphs_scrollbar.set
)

graphs_scroll_canvas.grid(
    row=0,
    column=0,
    sticky="nsew"
)

graphs_scrollbar.grid(
    row=0,
    column=1,
    sticky="ns"
)

# Inner frame containing all graphs
graphs_container = tk.Frame(
    graphs_scroll_canvas,
    bg=BG
)

graphs_window = graphs_scroll_canvas.create_window(
    (0, 0),
    window=graphs_container,
    anchor="nw"
)

def update_graph_scroll_region(event=None):
    graphs_scroll_canvas.configure(
        scrollregion=graphs_scroll_canvas.bbox("all")
    )

def resize_graph_container(event):
    graphs_scroll_canvas.itemconfigure(
        graphs_window,
        width=event.width
    )

graphs_container.bind(
    "<Configure>",
    update_graph_scroll_region
)

graphs_scroll_canvas.bind(
    "<Configure>",
    resize_graph_container
)

# Mouse wheel scrolling
def scroll_graphs(event):
    graphs_scroll_canvas.yview_scroll(
        int(-1 * (event.delta / 120)),
        "units"
    )

graphs_scroll_canvas.bind_all(
    "<MouseWheel>",
    scroll_graphs
)

# Individual graph canvases
def create_graph_canvas(parent):

    canvas = tk.Canvas(
        parent,
        bg=DARK,
        height=240,
        highlightthickness=1,
        highlightbackground="#334155"
    )

    canvas.pack(
        fill="x",
        expand=False,
        padx=10,
        pady=8
    )

    return canvas

rtt_canvas = create_graph_canvas(graphs_container)

encapsulation_canvas = create_graph_canvas(graphs_container)

packet_size_canvas = create_graph_canvas(graphs_container)

# ============================================================
# PERFORMANCE HISTORY WINDOW
# ============================================================

history_window = None

history_tree = None


def open_history_window():

    global history_window, history_tree

    # Create the window only once.

    if history_window is None or not history_window.winfo_exists():

        history_window = tk.Toplevel(root)

        history_window.title("OSI Performance History")

        history_window.geometry("850x420")

        history_window.configure(bg=BG)

        history_window.protocol(

            "WM_DELETE_WINDOW",

            history_window.withdraw

        )

        tk.Label(

            history_window,

            text="SIMULATION PERFORMANCE HISTORY",

            bg=BG,

            fg=WHITE,

            font=("Segoe UI", 13, "bold")

        ).pack(

            anchor="w",

            padx=15,

            pady=12

        )

        table_frame = tk.Frame(

            history_window,

            bg=BG

        )

        table_frame.pack(

            fill="both",

            expand=True,

            padx=12,

            pady=8

        )

        columns = (

            "simulation",

            "PACKET_BYTES",

            "ENCAPSULATION_MS",

            "RTT_MS",

            "TOTAL_CLIENT_MS"

        )

        history_tree = ttk.Treeview(

            table_frame,

            columns=columns,

            show="headings"

        )

        headings = {

            "simulation": "Run",

            "PACKET_BYTES": "Packet Size (Bytes)",

            "ENCAPSULATION_MS": "Encapsulation (ms)",

            "RTT_MS": "RTT (ms)",

            "TOTAL_CLIENT_MS": "Total Client Time (ms)"

        }

        widths = {

            "simulation": 70,

            "PACKET_BYTES": 140,

            "ENCAPSULATION_MS": 160,

            "RTT_MS": 120,

            "TOTAL_CLIENT_MS": 170

        }

        for column in columns:

            history_tree.heading(

                column,

                text=headings[column]

            )

            history_tree.column(

                column,

                width=widths[column],

                anchor="center"

            )

        scrollbar = ttk.Scrollbar(

            table_frame,

            orient="vertical",

            command=history_tree.yview

        )

        history_tree.configure(

            yscrollcommand=scrollbar.set

        )

        history_tree.pack(

            side="left",

            fill="both",

            expand=True

        )

        scrollbar.pack(

            side="right",

            fill="y"

        )

        button_frame = tk.Frame(

            history_window,

            bg=BG

        )

        button_frame.pack(

            fill="x",

            padx=12,

            pady=10

        )

        tk.Button(

            button_frame,

            text="EXPORT CSV",

            command=export_history_to_csv,

            bg=BLUE,

            fg=WHITE,

            relief="flat",

            padx=12,

            pady=7

        ).pack(

            side="left",

            padx=4

        )

        tk.Button(

            button_frame,

            text="EXPORT JSON",

            command=export_history_to_json,

            bg="#334155",

            fg=WHITE,

            relief="flat",

            padx=12,

            pady=7

        ).pack(

            side="left",

            padx=4

        )

        tk.Button(

            button_frame,

            text="CLOSE",

            command=history_window.withdraw,

            bg="#991B1B",

            fg=WHITE,

            relief="flat",

            padx=12,

            pady=7

        ).pack(

            side="right",

            padx=4

        )

    update_history_table()

    history_window.deiconify()

    history_window.lift()

    history_window.focus_force()


# ============================================================
# UPDATE HISTORY TABLE SAFELY
# ============================================================

def update_history_table():

    global history_tree

    if history_tree is None:

        return

    if not history_tree.winfo_exists():

        return

    history_tree.delete(

        *history_tree.get_children()

    )

    for record in performance_history:

        history_tree.insert(

            "",

            "end",

            values=(

                record["simulation"],

                f"{record['PACKET_BYTES']:.0f}",

                f"{record['ENCAPSULATION_MS']:.4f}",

                f"{record['RTT_MS']:.4f}",

                f"{record['TOTAL_CLIENT_MS']:.4f}"

            )

        )


# ============================================================
# WINDOW CLOSE HANDLER
# ============================================================

def on_application_close():

    global running

    if running:

        confirm = messagebox.askyesno(

            "Simulation Running",

            "A simulation is currently running. "

            "Do you want to close the application?"

        )

        if not confirm:

            return

    save_history_to_json()

    root.destroy()


# ============================================================
# APPLICATION INITIALIZATION
# ============================================================

def initialize_application():

    # Draw initial packet flow.

    draw_packet_flow()

    # Show initial OSI layer information.

    show_layer_details(7)

    # Restore previous performance records.

    load_history_from_json()

    # Set initial status.

    status.configure(

        text="● SYSTEM READY",

        fg=GREEN

    )

    connection.configure(

        text="SERVER: STOPPED    CLIENT: IDLE",

        fg=GRAY

    )

    write_log(

        "[SYSTEM] OSI Network Simulator initialized."

    )

    write_log(

        "[SYSTEM] Ready to establish TCP communication."

    )

    write_log(

        "[SYSTEM] Select a message and click START SIMULATION."

    )

    # Start checking background process events.

    root.after(

        50,

        poll_events

    )

    # Handle window close.

    root.protocol(

        "WM_DELETE_WINDOW",

        on_application_close

    )


# ============================================================
# START APPLICATION
# ============================================================

initialize_application()

root.mainloop()