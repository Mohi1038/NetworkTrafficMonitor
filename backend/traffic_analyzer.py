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
BASE_DIR = Path(__file__).parent
DATA_FILE = BASE_DIR / "network_data.json"
TEMP_FILE = BASE_DIR / "network_data_tmp.json"

stats = {
    "total_incoming_bytes": 0,
    "total_outgoing_bytes": 0,
    "speed": {
        "incoming_mbps": 0,
        "outgoing_mbps": 0,
        "incoming_kbps": 0,  # Backward compatibility
        "outgoing_kbps": 0   # Backward compatibility
    },
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
    try:
        connections = psutil.net_connections(kind='inet')
    except (psutil.AccessDenied, PermissionError):
        port_process_cache[port] = None
        return None

    for conn in connections:
        if conn.laddr and conn.laddr.port == port and conn.pid:
            try:
                proc = psutil.Process(conn.pid)
                name = proc.name()
                port_process_cache[port] = name
                return name
            except (psutil.AccessDenied, psutil.NoSuchProcess, PermissionError):
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
            "direction": direction,
            "bytes": size
        })

# Save JSON every second (batched write)
def json_writer_loop():
    while True:
        time.sleep(1)
        save_to_json()

# Speed calculation history for smooth averaging (like Akamai/Ookla)
speed_samples = {'incoming': [], 'outgoing': []}
MAX_SPEED_SAMPLES = 10  # Keep 10 samples for averaging

def update_speed_loop():
    with lock:
        prev_in = stats["total_incoming_bytes"]
        prev_out = stats["total_outgoing_bytes"]

    while True:
        time.sleep(1)
        with lock:
            curr_in = stats["total_incoming_bytes"]
            curr_out = stats["total_outgoing_bytes"]
            
            # Calculate instantaneous speed in Mbps (megabits per second)
            # Formula: (bytes * 8 bits/byte) / (1 second) / (1,000,000 bits/Mb)
            bytes_in_delta = curr_in - prev_in
            bytes_out_delta = curr_out - prev_out
            
            incoming_mbps = round((bytes_in_delta * 8) / 1_000_000, 2)
            outgoing_mbps = round((bytes_out_delta * 8) / 1_000_000, 2)
            
            # Store samples for averaging (smooth out spikes)
            speed_samples['incoming'].append(incoming_mbps)
            speed_samples['outgoing'].append(outgoing_mbps)
            
            # Keep only the last MAX_SPEED_SAMPLES
            if len(speed_samples['incoming']) > MAX_SPEED_SAMPLES:
                speed_samples['incoming'].pop(0)
            if len(speed_samples['outgoing']) > MAX_SPEED_SAMPLES:
                speed_samples['outgoing'].pop(0)
            
            # Calculate moving average (more stable than instantaneous)
            avg_incoming = round(sum(speed_samples['incoming']) / len(speed_samples['incoming']), 2)
            avg_outgoing = round(sum(speed_samples['outgoing']) / len(speed_samples['outgoing']), 2)
            
            # Update stats with averaged values (Mbps)
            stats["speed"]["incoming_mbps"] = avg_incoming
            stats["speed"]["outgoing_mbps"] = avg_outgoing
            
            # Also keep backward compatibility with kbps
            stats["speed"]["incoming_kbps"] = round(avg_incoming * 1000, 2)
            stats["speed"]["outgoing_kbps"] = round(avg_outgoing * 1000, 2)
            
            prev_in, prev_out = curr_in, curr_out

load_existing_data()

# Start both background threads safely
threading.Thread(target=update_speed_loop, daemon=True).start()
threading.Thread(target=json_writer_loop, daemon=True).start()
