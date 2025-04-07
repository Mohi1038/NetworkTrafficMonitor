# capture.py
import time
from datetime import datetime
from collections import defaultdict
import pandas as pd
from scapy.all import sniff, IP, TCP, UDP

# 1. Data structure to hold per‐flow stats
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

# 2. Packet handler
def process_packet(pkt):
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

    # Start/end times
    if f['start_time'] is None:
        f['start_time'] = now
    else:
        f['iat_list'].append(now - f['last_time'])
    f['last_time'] = now

    # Packet & byte counts
    f['packet_count'] += 1
    length = len(pkt)
    f['byte_count'] += length
    f['packet_sizes'].append(length)

    # TTL & window
    f['ttl_list'].append(ip.ttl)
    if proto=='TCP':
        tcp = pkt[TCP]
        f['win_list'].append(tcp.window)
        flags = tcp.flags
        if flags & 0x02: f['syn_count'] += 1
        if flags & 0x10: f['ack_count'] += 1

# 3. Capture for N seconds
if __name__ == "__main__":
    print("Sniffing for 30 seconds...")
    sniff(timeout=30, prn=process_packet, store=False)
    print("Done. Aggregating flows...")

    # 4. Build DataFrame
    records = []
    for (src, dst, sp, dp, proto), f in flows.items():
        duration = (f['last_time'] - f['start_time']) if f['start_time'] else 0
        iats = f['iat_list'] or [0]
        pkt_sizes = f['packet_sizes'] or [0]
        wins = f['win_list'] or [0]
        ttls = f['ttl_list'] or [0]

        records.append({
            'src_ip': src,
            'dst_ip': dst,
            'src_port': sp,
            'dst_port': dp,
            'protocol': proto,
            'flow_duration': duration,
            'packet_count': f['packet_count'],
            'byte_count': f['byte_count'],
            'avg_pkt_size': sum(pkt_sizes)/len(pkt_sizes),
            'std_pkt_size': pd.Series(pkt_sizes).std(),
            'mean_iat': sum(iats)/len(iats),
            'std_iat': pd.Series(iats).std(),
            'syn_count': f['syn_count'],
            'ack_count': f['ack_count'],
            'avg_ttl': sum(ttls)/len(ttls),
            'avg_win': sum(wins)/len(wins),
        })

    df = pd.DataFrame(records)
    df.to_csv("realtime_flow_features.csv", index=False)
    print("Saved realtime_flow_features.csv with", len(df), "flows.")
