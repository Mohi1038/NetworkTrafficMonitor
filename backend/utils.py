from scapy.all import get_working_if, get_if_addr

def get_active_ip():
    iface = get_working_if()
    return iface, get_if_addr(iface)
