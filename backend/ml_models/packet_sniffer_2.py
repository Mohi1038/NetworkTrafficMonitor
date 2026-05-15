import time
import joblib
import numpy as np
import pandas as pd
from collections import defaultdict
from scapy.all import sniff, IP, TCP, UDP
import warnings

warnings.filterwarnings("ignore")

# Load model and preprocessing
model = joblib.load("rf_model.pkl")
scaler = joblib.load("scaler.pkl")
pca = joblib.load("pca.pkl")

print("[+] Model, scaler, PCA loaded.")

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

        # Add dummy values to match required 13 features
        while len(features) < 13:
            features.append(0.0)

        records.append((src, dst, proto, features))
    return records

def process_packet(pkt, flows):
    if not pkt.haslayer(IP):
        return
    ip = pkt[IP]
    proto = 'TCP' if pkt.haslayer(TCP) else ('UDP' if pkt.haslayer(UDP) else 'OTHER')
    sport = pkt[TCP].sport if proto=='TCP' else (pkt[UDP].sport if proto=='UDP' else None)
    dport = pkt[TCP].dport if proto=='TCP' else (pkt[UDP].dport if proto=='UDP' else None)
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
        if flags & 0x02: f['syn_count'] += 1
        if flags & 0x10: f['ack_count'] += 1

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
            else:
                print(f"[✅] Flow from {src} to {dst} is benign ({proto})")
        except Exception as e:
            print("[Prediction Error]", e)

if __name__ == "__main__":
    print(" Starting continuous flow-based prediction...")
    try:
        while True:
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

            print(" Capturing for 30 seconds...")
            sniff(timeout=30, prn=lambda pkt: process_packet(pkt, flows), store=False)

            print(" Extracting & predicting...")
            features = extract_flow_features(flows)
            predict_flows(features)
            print(" Restarting capture... Press Ctrl+C to stop\n")

    except KeyboardInterrupt:
        print("\n Stopped by user. Exiting...")