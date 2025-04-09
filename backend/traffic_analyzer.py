
# ####### After JSON #####
import json
import time
import threading
from collections import defaultdict
from pathlib import Path
import os
import socket
import psutil
import threading

lock = threading.RLock()
DATA_FILE = "network_data.json"
TEMP_FILE = "network_data_tmp.json"

stats = {
    "total_incoming_bytes": 0,
    "total_outgoing_bytes": 0,
    "speed": {"incoming_kbps": 0, "outgoing_kbps": 0},
    "protocol_distribution": defaultdict(int),
    # "top_ips": defaultdict(int),
    # "top_ips": defaultdict(lambda: {"hostname": "", "app": "", "total_bytes": 0}),
    "top_ips": defaultdict(lambda: {"hostname": "", "app": "", "incoming_bytes": 0, "outgoing_bytes": 0}),
    
    "traffic_table": []
}

def load_existing_data():
    if Path(DATA_FILE).exists():
        try:
            with open(DATA_FILE, "r") as f:
                old_data = json.load(f)

            stats["total_incoming_bytes"] = old_data.get("total_incoming_bytes", 0)
            stats["total_outgoing_bytes"] = old_data.get("total_outgoing_bytes", 0)
            stats["speed"] = old_data.get("speed", {"incoming_kbps": 0, "outgoing_kbps": 0})

            for proto, count in old_data.get("protocol_distribution", {}).items():
                stats["protocol_distribution"][proto] += count

            for ip, ip_data in old_data.get("top_ips", {}).items():
                stats["top_ips"][ip]["hostname"] = ip_data.get("hostname", "")
                stats["top_ips"][ip]["app"] = ip_data.get("app", "")
                stats["top_ips"][ip]["incoming_bytes"] += ip_data.get("incoming_bytes", 0)
                stats["top_ips"][ip]["outgoing_bytes"] += ip_data.get("outgoing_bytes", 0)

            stats["traffic_table"].extend(old_data.get("traffic_table", []))

        except Exception as e:
            print(f"[Error loading saved data] {e}")


if not Path(TEMP_FILE).exists():
    with open(TEMP_FILE, "w") as f:
        json.dump({}, f)
# Ensure file exists once
if not Path(DATA_FILE).exists():
    with open(DATA_FILE, "w") as f:
        json.dump({}, f)


def atomic_write_json(data, filename):
    with open(DATA_FILE, "w") as f:
        json.dump(data, f, indent=2)

def save_to_json():
    with lock:
        atomic_write_json({
            "total_incoming_bytes": stats["total_incoming_bytes"],
            "total_outgoing_bytes": stats["total_outgoing_bytes"],
            "speed": stats["speed"],
            "protocol_distribution": dict(stats["protocol_distribution"]),
            "top_ips": dict(stats["top_ips"]),
            
            "traffic_table": stats["traffic_table"][-100:]  # Keep recent 100
        }, DATA_FILE)


# Function to get hostname from IP
def get_hostname(ip):
    if ip in ip_hostname_cache:
        return ip_hostname_cache[ip]
    try:
        hostname = socket.gethostbyaddr(ip)[0]
    except Exception:
        hostname = ip  # fallback
    ip_hostname_cache[ip] = hostname
    return hostname

ip_hostname_cache = {}
port_process_cache = {}
# Function to get process name from port
def get_process_name_by_port(port):
    if port in port_process_cache:
        return port_process_cache[port]
    for conn in psutil.net_connections(kind='inet'):
        if conn.laddr and conn.laddr.port == port:
            try:
                proc = psutil.Process(conn.pid)
                name = proc.name()
                port_process_cache[port] = name
                return name
            except Exception:
                continue
    port_process_cache[port] = None
    return None

def update_stats(src_ip, src_port, dst_ip, dst_port, protocol, size, direction):
    with lock:
        if direction == "incoming":
            stats["total_incoming_bytes"] += size
        else:
            stats["total_outgoing_bytes"] += size

        # ip_key = dst_ip if direction == "outgoing" else src_ip
        # port = dst_port if direction == "outgoing" else src_port

        # # stats["top_ips"][ip_key] += size
        # stats["top_ips"][ip_key]["hostname"] = get_hostname(ip_key)
        # stats["top_ips"][ip_key]["app"] = get_process_name_by_port(port)
        # stats["top_ips"][ip_key]["total_bytes"]+= size

        if direction == "outgoing":
            ip_key = dst_ip
            port = dst_port

            stats["top_ips"][ip_key]["hostname"] = get_hostname(ip_key)
            stats["top_ips"][ip_key]["app"] = get_process_name_by_port(port)
            stats["top_ips"][ip_key]["outgoing_bytes"]+= size
        else:
            ip_key = src_ip
            port = src_port

            stats["top_ips"][ip_key]["hostname"] = get_hostname(ip_key)
            stats["top_ips"][ip_key]["app"] = get_process_name_by_port(port)
            stats["top_ips"][ip_key]["incoming_bytes"]+= size

        stats["protocol_distribution"][protocol] += size

        stats["traffic_table"].append({
            "timestamp": time.strftime("%H:%M:%S"),
            "src_ip": src_ip,
            "src_port": src_port,
            "dst_ip": dst_ip,
            "dst_port": dst_port,
            "protocol": protocol,
            "bytes": size
        })

# Save JSON every second (batched write)
def json_writer_loop():
    while True:
        time.sleep(1)
        save_to_json()

def update_speed_loop():
    prev_in, prev_out = 0, 0
    while True:
        time.sleep(1)
        with lock:
            curr_in = stats["total_incoming_bytes"]
            curr_out = stats["total_outgoing_bytes"]
            stats["speed"]["incoming_kbps"] = round((curr_in - prev_in) * 8 / 1000, 2)
            stats["speed"]["outgoing_kbps"] = round((curr_out - prev_out) * 8 / 1000, 2)
            prev_in, prev_out = curr_in, curr_out

load_existing_data()

# Start both background threads safely
threading.Thread(target=update_speed_loop, daemon=True).start()
threading.Thread(target=json_writer_loop, daemon=True).start()
