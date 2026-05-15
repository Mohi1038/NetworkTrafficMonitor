# utils.py
import socket
import psutil

def get_active_ip():
    """
    Returns the active network interface and its IP address.
    """
    interfaces = psutil.net_if_addrs()
    for iface_name, iface_addrs in interfaces.items():
        for addr in iface_addrs:
            if addr.family == socket.AF_INET and not addr.address.startswith("127."):
                return iface_name, addr.address
    return None, None
