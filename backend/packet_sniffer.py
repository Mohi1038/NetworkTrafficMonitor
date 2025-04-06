# from scapy.all import sniff, IP, IPv6, TCP, UDP, ARP, Ether
# from traffic_analyzer import update_stats
# from utils import get_active_ip

# ifac,my_ip = get_active_ip()

# def process_packet(packet):
#     try:
#         src_ip, dst_ip = "N/A", "N/A"
#         src_port, dst_port = "N/A", "N/A"
#         protocol = "UNKNOWN"
#         service = "N/A"
#         size = len(packet)  # Packet size in bytes

#         # Detect protocol based on layers
#         if ARP in packet:
#             protocol = "ARP"
#             src_ip = packet[ARP].psrc
#             dst_ip = packet[ARP].pdst
#         elif IP in packet:
#             src_ip = packet[IP].src
#             dst_ip = packet[IP].dst
#             proto = packet[IP].proto
#             if TCP in packet:
#                 protocol = "TCP"
#                 src_port = packet[TCP].sport
#                 dst_port = packet[TCP].dport
#             elif UDP in packet:
#                 protocol = "UDP"
#                 src_port = packet[UDP].sport
#                 dst_port = packet[UDP].dport
#             elif proto == 1:
#                 protocol = "ICMP"
#             else:
#                 protocol = f"IP_PROTO_{proto}"
#         elif IPv6 in packet:
#             src_ip = packet[IPv6].src
#             dst_ip = packet[IPv6].dst
#             proto = packet[IPv6].nh
#             if TCP in packet:
#                 protocol = "TCPv6"
#                 src_port = packet[TCP].sport
#                 dst_port = packet[TCP].dport
#             elif UDP in packet:
#                 protocol = "UDPv6"
#                 src_port = packet[UDP].sport
#                 dst_port = packet[UDP].dport
#             elif proto == 58:
#                 protocol = "ICMPv6"
#             else:
#                 protocol = f"IPv6_PROTO_{proto}"
#         elif Ether in packet:
#             protocol = packet[Ether].type  # Lower level protocol (e.g., 0x0806 = ARP)

#         # Decide direction
#         direction = "incoming"
#         if src_ip == my_ip:
#             direction = "outgoing"

#         update_stats(
#             src_ip, src_port,
#             dst_ip, dst_port,
#             protocol, size, direction
#         )

#     except Exception as e:
#         print(f"[!] Packet processing error: {e}")

# def start_sniffing():
#     # No BPF filter — capture all packets
#     sniff(iface=ifac, prn=process_packet, store=False)


# ####### After JSON #####
from scapy.all import sniff, IP, IPv6, TCP, UDP, ARP, Ether
from traffic_analyzer import update_stats
from utils import get_active_ip

ifac,my_ip = get_active_ip()

def process_packet(packet):
    try:
        size = len(bytes(packet))  # ✅ accurate size in bytes
        src_ip, dst_ip = "N/A", "N/A"
        src_port, dst_port = "N/A", "N/A"
        protocol = "UNKNOWN"

        if ARP in packet:
            protocol = "ARP"
            src_ip, dst_ip = packet[ARP].psrc, packet[ARP].pdst
        elif IP in packet:
            src_ip, dst_ip = packet[IP].src, packet[IP].dst
            if TCP in packet:
                protocol = "TCP"
                src_port, dst_port = packet[TCP].sport, packet[TCP].dport
            elif UDP in packet:
                protocol = "UDP"
                src_port, dst_port = packet[UDP].sport, packet[UDP].dport
            else:
                protocol = f"IP_PROTO_{packet[IP].proto}"
        elif IPv6 in packet:
            src_ip, dst_ip = packet[IPv6].src, packet[IPv6].dst
            if TCP in packet:
                protocol = "TCPv6"
                src_port, dst_port = packet[TCP].sport, packet[TCP].dport
            elif UDP in packet:
                protocol = "UDPv6"
                src_port, dst_port = packet[UDP].sport, packet[UDP].dport
            else:
                protocol = f"IPv6_PROTO_{packet[IPv6].nh}"
        elif Ether in packet:
            protocol = hex(packet[Ether].type)

        direction = "incoming" if src_ip != my_ip else "outgoing"
        update_stats(src_ip, src_port, dst_ip, dst_port, protocol, size, direction)
    except Exception as e:
        print("[ERROR processing packet]", e)

def start_sniffing():
    sniff(iface=ifac, prn=process_packet, store=False)
