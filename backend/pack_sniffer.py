import time
import joblib
import numpy as np
import pandas as pd
import threading
from collections import defaultdict
from scapy.all import sniff, IP, IPv6, TCP, UDP, ARP, Ether
from traffic_analyzer import update_stats
from utils import get_active_ip
import warnings

warnings.filterwarnings("ignore")

# Load model, scaler, PCA (FIXED PATHS)
model = joblib.load("./backend/ml_model/ml _model/rf_model.pkl")
scaler = joblib.load("./backend/ml_model/ml _model/scaler.pkl")
pca = joblib.load("./backend/ml_model/ml _model/pca.pkl")
print("[+] Model, scaler, PCA loaded.")

# Get interface and local IP
iface, my_ip = get_active_ip()

# Global callback holder
alert_callback = None

def set_alert_callback(callback):
    global alert_callback
    alert_callback = callback
    print("[+] Alert callback set successfully.")

# Filter out noisy/irrelevant packets
def is_irrelevant_packet(packet, size):
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

# JSON-like update handler
def process_packet_json(packet):
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
        print("[ERROR processing packet]", e)

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

# Flow processor
def process_packet_flow(pkt):
    if not pkt.haslayer(IP):
        return
    ip = pkt[IP]
    proto = 'TCP' if pkt.haslayer(TCP) else ('UDP' if pkt.haslayer(UDP) else 'OTHER')
    sport = pkt[TCP].sport if proto == 'TCP' else (pkt[UDP].sport if proto == 'UDP' else None)
    dport = pkt[TCP].dport if proto == 'TCP' else (pkt[UDP].dport if proto == 'UDP' else None)
    if sport is None or dport is None:
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
        if flags & 0x02:
            f['syn_count'] += 1
        if flags & 0x10:
            f['ack_count'] += 1

# Feature extractor
def extract_flow_features(flows):
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
            pd.Series(pkt_sizes).std() or 0,
            sum(iats) / len(iats),
            pd.Series(iats).std() or 0,
            f['syn_count'],
            f['ack_count'],
            sum(ttls) / len(ttls),
            sum(wins) / len(wins)
        ]

        while len(features) < 13:
            features.append(0.0)

        records.append((src, dst, proto, features))
    return records

# ML Prediction
def predict_flows(flow_features):
    for src, dst, proto, feat in flow_features:
        try:
            X = np.array(feat).reshape(1, -1)
            X_scaled = scaler.transform(X)
            X_scaled = np.nan_to_num(X_scaled, nan=0.0)
            X_pca = pca.transform(X_scaled)
            pred = model.predict(X_pca)[0]
            if pred != "BENIGN":
                print(f"[⚠️] Attack detected: {pred} from {src} to {dst} ({proto})")
                if alert_callback:
                    print("[CALLBACK DEBUG] Triggering alert callback...")
                    alert_callback(pred, src, dst, proto)
            else:
                print(f"[✅] Flow from {src} to {dst} is benign ({proto})")
        except Exception as e:
            print("[Prediction Error]", e)

# Combined handler
def combined_packet_handler(pkt):
    process_packet_json(pkt)
    process_packet_flow(pkt)

# Timer-based prediction
def run_prediction_after_interval(interval_sec):
    def delayed_predict():
        while True:
            time.sleep(interval_sec)
            print("\n[+] Interval reached. Extracting & predicting...\n")
            features = extract_flow_features(flows)
            predict_flows(features)

    threading.Thread(target=delayed_predict, daemon=True).start()

# Start sniffing
print("[*] Starting sniffing on interface:", iface)
run_prediction_after_interval(10)

def start_sniffing():
    print("[*] Sniffing packets...")
    sniff(iface=iface, prn=combined_packet_handler, store=False)
