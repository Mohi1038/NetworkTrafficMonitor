import time
import os
import sys
import threading
import math
from collections import defaultdict
from pathlib import Path

import warnings
warnings.filterwarnings("ignore")

# Check for root/admin privileges
def check_privileges():
    """Warn if not running with appropriate privileges"""
    if os.name == 'posix':  # Linux/macOS
        if os.geteuid() != 0:
            print("[⚠️  WARNING] Not running as root. Packet capture may fail.")
            print("[INFO] Try running with: sudo python3 app2.py")
            return False
    return True

check_privileges()

from scapy.all import sniff, IP, IPv6, TCP, UDP, ARP, Ether
from traffic_analyzer import update_stats
from utils import get_active_ip
from dpi_engine import inspect_packet as inspect_dpi_packet


def _stddev(values):
    """Compute population stddev without importing heavy data libs at startup."""
    if not values or len(values) < 2:
        return 0.0
    mean = sum(values) / len(values)
    variance = sum((v - mean) ** 2 for v in values) / len(values)
    return math.sqrt(variance)

# Try to import ML inference module only when explicitly enabled.
ML_ENABLED = False
ml_engine = None
if os.environ.get("NTM_ENABLE_ML", "0").strip() == "1":
    try:
        from ml_models.ml_inference import get_ml_engine
        ml_engine = get_ml_engine()
        ML_ENABLED = bool(getattr(ml_engine, "is_loaded", False))
        print("[+] ML inference module loaded successfully.")
    except Exception as e:
        print(f"[⚠️  WARNING] Could not load ML module: {e}")
        print("[INFO] Running without ML threat detection.")

# Get interface and local IP
iface, my_ip = get_active_ip()

# Global callback holder
alert_callback = None

def set_alert_callback(callback):
    """Set the callback function for alerts"""
    global alert_callback
    alert_callback = callback
    print("[+] Alert callback set successfully.")

# Filter out noisy/irrelevant packets
def is_irrelevant_packet(packet, size):
    """Filter out broadcast, local, and noisy packets"""
    if packet.haslayer(ARP):
        return True
    if Ether in packet and packet[Ether].dst == "ff:ff:ff:ff:ff:ff":
        return True
    if IP in packet:
        ip = packet[IP]
        if ip.src.startswith("127.") or ip.dst.startswith("127."):
            return True
        if ip.dst.endswith(".255") or ip.dst.startswith("224."):
            return True
        if UDP in packet:
            if packet[UDP].sport in [137, 138, 139, 5353, 67, 68, 1900, 5355, 3702]:
                return True
            if size < 80:
                return True
    if IPv6 in packet:
        ip6 = packet[IPv6]
        if ip6.src == "::1" or ip6.dst == "::1":
            return True
        if ip6.dst.startswith("ff"):
            return True
    return False

# Packet processor for traffic analysis
def process_packet_json(packet):
    """Process packet and update traffic statistics"""
    try:
        size = len(bytes(packet))
        src_ip, dst_ip = "N/A", "N/A"
        src_port, dst_port = "N/A", "N/A"
        protocol = "UNKNOWN"

        if ARP in packet:
            protocol = "ARP"
            src_ip, dst_ip = packet[ARP].psrc, packet[ARP].pdst

        elif IP in packet:
            src_ip, dst_ip = packet[IP].src, packet[IP].dst
            if TCP in packet:
                src_port, dst_port = packet[TCP].sport, packet[TCP].dport
                if dst_port == 80 or src_port == 80:
                    protocol = "HTTP"
                elif dst_port == 443 or src_port == 443:
                    protocol = "HTTPS"
                else:
                    protocol = "TCP"
            elif UDP in packet:
                src_port, dst_port = packet[UDP].sport, packet[UDP].dport
                protocol = "UDP"
            else:
                protocol = f"IP_PROTO_{packet[IP].proto}"

        elif IPv6 in packet:
            src_ip, dst_ip = packet[IPv6].src, packet[IPv6].dst
            if TCP in packet:
                src_port, dst_port = packet[TCP].sport, packet[TCP].dport
                if dst_port == 80 or src_port == 80:
                    protocol = "HTTP"
                elif dst_port == 443 or src_port == 443:
                    protocol = "HTTPS"
                else:
                    protocol = "TCPv6"
            elif UDP in packet:
                src_port, dst_port = packet[UDP].sport, packet[UDP].dport
                protocol = "UDPv6"
            else:
                protocol = f"IPv6_PROTO_{packet[IPv6].nh}"

        elif Ether in packet:
            protocol = hex(packet[Ether].type)

        direction = "incoming" if src_ip != my_ip else "outgoing"
        update_stats(src_ip, src_port, dst_ip, dst_port, protocol, size, direction)

    except Exception as e:
        print(f"[ERROR] Packet processing error: {e}")

# Flow feature tracker
flows = defaultdict(lambda: {
    'start_time': None,
    'last_time': None,
    'packet_count': 0,
    'byte_count': 0,
    'packet_sizes': [],
    'iat_list': [],
    'syn_count': 0,
    'ack_count': 0,
    'ttl_list': [],
    'win_list': []
})

# Process packets for flow-based ML detection
def process_packet_flow(pkt):
    """Extract flow features from packet"""
    if not pkt.haslayer(IP):
        return

    ip = pkt[IP]
    proto = 'TCP' if pkt.haslayer(TCP) else ('UDP' if pkt.haslayer(UDP) else 'OTHER')

    if proto == 'TCP':
        sport = pkt[TCP].sport
        dport = pkt[TCP].dport
    elif proto == 'UDP':
        sport = pkt[UDP].sport
        dport = pkt[UDP].dport
    else:
        return

    flow_key = (ip.src, ip.dst, sport, dport, proto)
    now = time.time()
    f = flows[flow_key]

    if f['start_time'] is None:
        f['start_time'] = now
    else:
        f['iat_list'].append(now - f['last_time'])
    f['last_time'] = now

    length = len(pkt)
    f['packet_count'] += 1
    f['byte_count'] += length
    f['packet_sizes'].append(length)
    f['ttl_list'].append(ip.ttl)

    if proto == 'TCP':
        tcp = pkt[TCP]
        f['win_list'].append(tcp.window)
        flags = tcp.flags
        if flags & 0x02:  # SYN flag
            f['syn_count'] += 1
        if flags & 0x10:  # ACK flag
            f['ack_count'] += 1

# Extract features from flows
def extract_flow_features(flows):
    """Extract ML features from network flows"""
    records = []
    for (src, dst, sp, dp, proto), f in flows.items():
        duration = (f['last_time'] - f['start_time']) if f['start_time'] else 0
        iats = f['iat_list'] or [0]
        pkt_sizes = f['packet_sizes'] or [0]
        wins = f['win_list'] or [0]
        ttls = f['ttl_list'] or [0]

        features = [
            duration,
            f['packet_count'],
            f['byte_count'],
            sum(pkt_sizes) / len(pkt_sizes),
            _stddev(pkt_sizes),
            sum(iats) / len(iats) if iats else 0,
            _stddev(iats),
            f['syn_count'],
            f['ack_count'],
            sum(ttls) / len(ttls) if ttls else 0,
            sum(wins) / len(wins) if wins else 0
        ]

        while len(features) < 13:
            features.append(0.0)

        records.append((src, dst, sp, dp, proto, features))
    return records

# ML Prediction
def predict_flows(flow_features):
    """Predict anomalies using ML model"""
    if not ML_ENABLED or not ml_engine:
        return

    for src, dst, src_port, dst_port, proto, feat in flow_features:
        try:
            flow_data = {
                'src_ip': src,
                'dst_ip': dst,
                'src_port': src_port,
                'dst_port': dst_port,
                'protocol': proto,
                'flow_duration': feat[0],
                'packet_count': feat[1],
                'byte_count': feat[2],
                'avg_pkt_size': feat[3],
                'std_pkt_size': feat[4],
                'mean_iat': feat[5],
                'std_iat': feat[6],
                'syn_count': feat[7],
                'ack_count': feat[8],
                'avg_ttl': feat[9],
                'avg_win': feat[10]
            }

            result = ml_engine.predict(flow_data)

            if result['error'] is None and result['prediction'] == 1:
                print(f"[⚠️  ANOMALY DETECTED] {src} → {dst} ({proto})")
                print(f"[ML] Confidence: {result['confidence']:.2%}")

                if alert_callback:
                    alert_callback("Network Anomaly", src, dst, proto)

        except Exception as e:
            print(f"[ERROR] ML prediction error: {e}")

# Combined packet handler
def combined_packet_handler(pkt):
    """Main packet handler combining traffic analysis and ML detection"""
    try:
        size = len(bytes(pkt))
        if is_irrelevant_packet(pkt, size):
            return
        process_packet_json(pkt)
        packet_data, alerts = inspect_dpi_packet(pkt, local_ip=my_ip)
        if alerts and alert_callback:
            for alert in alerts:
                packet_info = alert.get("packet_data", packet_data) or packet_data
                attack_type = f"DPI: {alert.get('rule_name', 'Suspicious Payload')}"
                src = packet_info.get("src_ip", "unknown")
                dst = packet_info.get("dst_ip", "unknown")
                protocol = packet_info.get("application_protocol") or packet_info.get("protocol", "unknown")
                try:
                    alert_callback(attack_type, src, dst, protocol)
                except Exception as callback_error:
                    print(f"[ERROR] DPI alert callback failed: {callback_error}")
        if ML_ENABLED:
            process_packet_flow(pkt)
    except Exception as e:
        print(f"[ERROR] Packet handler error: {e}")

# Timer-based prediction
def run_prediction_after_interval(interval_sec):
    """Run ML predictions at regular intervals"""
    if not ML_ENABLED:
        return

    def delayed_predict():
        while True:
            time.sleep(interval_sec)
            try:
                features = extract_flow_features(flows)
                if features:
                    print(f"[ML] Analyzing {len(features)} flows...")
                    predict_flows(features)
                    # Clear old flows
                    flows.clear()
            except Exception as e:
                print(f"[ERROR] Prediction interval error: {e}")

    threading.Thread(target=delayed_predict, daemon=True).start()

# Start sniffing
print(f"[*] Starting network packet capture on interface: {iface}")
print(f"[*] Local IP: {my_ip}")
if ML_ENABLED:
    print("[+] ML threat detection: ENABLED")
    run_prediction_after_interval(10)
else:
    print("[*] ML threat detection: DISABLED (models not loaded)")

def start_sniffing():
    """Main function to start packet sniffing"""
    try:
        print("[*] Packet sniffer started. Listening for traffic...")
        sniff(iface=iface, prn=combined_packet_handler, store=False)
    except PermissionError:
        print("[ERROR] Packet capture requires root/admin privileges!")
        print("[INFO] Try running with: sudo python3 app2.py (Linux/macOS)")
        print("[INFO] Or run as Administrator (Windows)")
        return
    except Exception as e:
        print(f"[ERROR] Sniffing error: {e}")
        return
