import pandas as pd

# Load the historical dataset
df = pd.read_csv("n2_downsampled_filtered.csv", encoding="utf-8", on_bad_lines="skip")

# 1. Define a mapping from your long names to the short Scapy names
rename_map = {
    "Flow Duration": "flow_duration",
    "Total Fwd Packets": "packet_count",
    "Total Bwd Packets": "packet_count",            # we'll differentiate direction later if needed
    "Total Length of Fwd Packets": "byte_count",
    "Total Length of Bwd Packets": "byte_count",    # aggregate bytes
    "Fwd Packet Length Max": "avg_pkt_size",        # approximation: use avg in real-time
    "Fwd Packet Length Min": "std_pkt_size",        # approximation: use std in real-time
    "Fwd Packet Length Mean": "avg_pkt_size",
    "Fwd Packet Length Std": "std_pkt_size",
    "Bwd Packet Length Max": "avg_pkt_size",
    "Bwd Packet Length Min": "std_pkt_size",
    "Bwd Packet Length Mean": "avg_pkt_size",
    "Bwd Packet Length Std": "std_pkt_size",
    "Flow Bytes/s": "byte_count",                   # real-time byte rate
    "Flow Packets/s": "packet_count",               # real-time packet rate
    "Flow IAT Mean": "mean_iat",
    "Flow IAT Std": "std_iat",
    "Flow IAT Max": "max_iat",
    "Flow IAT Min": "min_iat",
    "FIN Flag Count": "syn_count",                  # approximate mapping
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

# 2. Rename columns
df = df.rename(columns=rename_map)

# 3. Define the final set of Scapy‐compatible features we can extract
final_cols = [
    "src_ip", "dst_ip",
    "src_port", "dst_port",
    "protocol", "flow_duration",
    "packet_count", "byte_count",
    "avg_pkt_size", "std_pkt_size",
    "mean_iat", "std_iat", "max_iat", "min_iat",
    "syn_count", "rst_count", "psh_count", "ack_count", "urg_count",
    "avg_win",
    "label"
]

# 4. Keep only those columns that actually exist in the DataFrame
existing = [c for c in final_cols if c in df.columns]
df = df[existing]

# 5. Save the reduced CSV
df.to_csv("n2_downsampled_filtered_2.csv", index=False, encoding="utf-8")
print("Reduced to Scapy‐compatible features:", existing)
