import pandas as pd

# 1. Load the reduced historical CSV
df = pd.read_csv("n2_downsampled_filtered_3.csv", encoding="utf-8")

print("Before reduction:", list(df.columns))

# 2. Define the features present in the Scapy output
scapy_features = [
    "src_ip", "dst_ip",
    "src_port", "dst_port",
    "protocol", "flow_duration",
    "packet_count", "byte_count",
    "avg_pkt_size", "std_pkt_size",
    "mean_iat", "std_iat",
    "syn_count", "ack_count",
    "avg_ttl", "avg_win"
]

# 3. Add 'label' to keep the target
if "label" in df.columns:
    scapy_features.append("label")

# 4. Filter the DataFrame to only these columns
existing = [c for c in scapy_features if c in df.columns]
df = df[existing]

# 5. Save back to CSV
df.to_csv("n2_downsampled_filtered_4.csv", index=False, encoding="utf-8")

print("After reduction:", existing)
