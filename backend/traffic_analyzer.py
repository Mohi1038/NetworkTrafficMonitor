# from collections import defaultdict, deque
# import time

# TRAFFIC_STATS = {
#     "incoming": deque(maxlen=200),
#     "outgoing": deque(maxlen=200),
#     "devices": defaultdict(int),
#     "protocols": defaultdict(int),
#     "detailed": defaultdict(lambda: {"bytes": 0, "packets": 0})
# }
# i=1
# def update_stats(src_ip, src_port, dst_ip, dst_port, proto, size, direction):
#     global i
#     now = time.time()

#     TRAFFIC_STATS[direction].append((now, size))
#     TRAFFIC_STATS["protocols"][proto] += size

#     ip_key = dst_ip if direction == "incoming" else src_ip
#     TRAFFIC_STATS["devices"][ip_key] += size

#     flow_key = (src_ip, src_port, dst_ip, dst_port, proto)
#     TRAFFIC_STATS["detailed"][flow_key]["bytes"] += size
#     TRAFFIC_STATS["detailed"][flow_key]["packets"] += 1

#     print(i)
#     i=i+1

# def get_speed(data):
#     now = time.time()
#     return sum(size for t, size in data if now - t <= 1)

# def get_traffic_summary():
#     incoming_speed = get_speed(TRAFFIC_STATS["incoming"])
#     outgoing_speed = get_speed(TRAFFIC_STATS["outgoing"])

#     top_devices = sorted(TRAFFIC_STATS["devices"].items(), key=lambda x: -x[1])[:5]
#     top_protocols = dict(TRAFFIC_STATS["protocols"])

#     detailed_table = []
#     for key, val in TRAFFIC_STATS["detailed"].items():
#         src_ip, src_port, dst_ip, dst_port, proto = key
#         detailed_table.append({
#             "src_ip": src_ip,
#             "src_port": src_port,
#             "dst_ip": dst_ip,
#             "dst_port": dst_port,
#             "protocol": proto,
#             "bytes": val["bytes"],
#             "packets": val["packets"]
#         })

#     return {
#         "area_chart": {
#             "incoming": sum(s for _, s in TRAFFIC_STATS["incoming"]),
#             "outgoing": sum(s for _, s in TRAFFIC_STATS["outgoing"])
#         },
#         "speedometer": {
#             "incoming_speed": incoming_speed*8/1000,
#             "outgoing_speed": outgoing_speed*8/1000
#         },
#         "top_devices": top_devices,
#         "protocol_distribution": top_protocols,
#         "traffic_table": detailed_table
#     }


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
from utils import stats

lock = threading.RLock()
DATA_FILE = "network_data.json"
TEMP_FILE = "network_data_tmp.json"

if not Path(TEMP_FILE).exists():
    with open(TEMP_FILE, "w") as f:
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

# Start both background threads safely
threading.Thread(target=update_speed_loop, daemon=True).start()
threading.Thread(target=json_writer_loop, daemon=True).start()
