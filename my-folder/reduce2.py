import pandas as pd

# 1. Load your historical CSV
df = pd.read_csv("n2_downsampled_filtered.csv", encoding="utf-8", on_bad_lines="skip")

# 2. Rename long names to Scapy names
rename_map = {
    "Flow Duration": "flow_duration",
    "Total Fwd Packets": "packet_count",
    "Total Bwd Packets": "packet_count",
    "Total Length of Fwd Packets": "byte_count",
    "Total Length of Bwd Packets": "byte_count",
    "Fwd Packet Length Max": "avg_pkt_size",
    "Fwd Packet Length Min": "std_pkt_size",
    "Fwd Packet Length Mean": "avg_pkt_size",
    "Fwd Packet Length Std": "std_pkt_size",
    "Bwd Packet Length Max": "avg_pkt_size",
    "Bwd Packet Length Min": "std_pkt_size",
    "Bwd Packet Length Mean": "avg_pkt_size",
    "Bwd Packet Length Std": "std_pkt_size",
    "Flow Bytes/s": "byte_count",
    "Flow Packets/s": "packet_count",
    "Flow IAT Mean": "mean_iat",
    "Flow IAT Std": "std_iat",
    "Flow IAT Max": "max_iat",
    "Flow IAT Min": "min_iat",
    "FIN Flag Count": "fin_count",
    "SYN Flag Count": "syn_count",
    "RST Flag Count": "rst_count",
    "PSH Flag Count": "psh_count",
    "ACK Flag Count": "ack_count",
    "URG Flag Count": "urg_count",
    "Init_Win_bytes_forward": "avg_win",
    "Init_Win_bytes_backward": "avg_win",
    "Protocol": "protocol",
    "Source Port": "src_port",
    "Destination Port": "dst_port",
    "Source IP": "src_ip",
    "Destination IP": "dst_ip",
    "Timestamp": "timestamp"
}
df.rename(columns=rename_map, inplace=True)

# 3. Drop original columns that were renamed (any duplicates)
#    We keep only one column for each new name.
df = df.loc[:, ~df.columns.duplicated()]

# 4. Define final Scapy‑compatible feature set + label
final_features = [
    "src_ip", "dst_ip",
    "src_port", "dst_port",
    "protocol", "flow_duration",
    "packet_count", "byte_count",
    "avg_pkt_size", "std_pkt_size",
    "mean_iat", "std_iat", "max_iat", "min_iat",
    "fin_count", "syn_count", "rst_count", "psh_count", "ack_count", "urg_count",
    "avg_win",
    "label"
]

# 5. Keep only those that exist
keep = [c for c in final_features if c in df.columns]
df = df[keep]

# 6. Save back
df.to_csv("n2_downsampled_filtered_3.csv", index=False, encoding="utf-8")

print("Final columns after reduction:")
print(keep)
