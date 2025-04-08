from scapy.all import get_working_if, get_if_addr
from collections import defaultdict

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

def get_active_ip():
    iface = get_working_if()
    return iface, get_if_addr(iface)
