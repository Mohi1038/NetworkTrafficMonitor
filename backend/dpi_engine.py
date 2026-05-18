"""
Deep Packet Inspection engine for local packet capture.

This module extracts application-layer fields from packets when available and
feeds the resulting packet context into the rule engine.
"""

from collections import defaultdict, deque
from datetime import datetime
import re
import socket
import threading

from scapy.all import ARP, Ether, IP, IPv6, Raw, TCP, UDP

try:
    from scapy.layers.dns import DNS, DNSQR
except Exception:  # pragma: no cover - optional scapy layer
    DNS = None
    DNSQR = None

try:
    from scapy.layers.tls.all import TLS, TLSClientHello
except Exception:  # pragma: no cover - optional scapy layer
    TLS = None
    TLSClientHello = None

from rule_engine import get_rule_engine


HTTP_METHOD_RE = re.compile(r"^(GET|POST|PUT|DELETE|HEAD|OPTIONS|PATCH|TRACE|CONNECT)\s+(\S+)\s+HTTP/(\d(?:\.\d)?)", re.IGNORECASE)
HTTP_STATUS_RE = re.compile(r"^HTTP/(\d(?:\.\d)?)\s+(\d{3})\s*(.*)$", re.IGNORECASE)
HEADER_RE = re.compile(r"^([^:]+):\s*(.*)$")


def _safe_text(value, limit=4096):
    if value is None:
        return ""
    if isinstance(value, bytes):
        text = value.decode("utf-8", errors="ignore")
    else:
        text = str(value)
    text = " ".join(text.split())
    return text[:limit]


def _safe_hex_preview(payload, limit=128):
    if not payload:
        return ""
    return payload[:limit].hex()


_domain_cache = {}


def _reverse_dns(ip_address):
    if not ip_address or ip_address in {"N/A", "unknown"}:
        return ""
    if ip_address in _domain_cache:
        return _domain_cache[ip_address]

    try:
        hostname = socket.gethostbyaddr(ip_address)[0]
    except Exception:
        hostname = ""

    _domain_cache[ip_address] = hostname
    return hostname


class DPIEngine:
    """Extract application-layer context and evaluate DPI rules."""

    def __init__(self, rule_engine=None):
        self.rule_engine = rule_engine or get_rule_engine()
        self.lock = threading.RLock()
        self.alerts = []
        self.packet_count = 0
        self.payload_packet_count = 0
        self.application_counts = defaultdict(int)
        self.protocol_counts = defaultdict(int)
        self.recent_packets = deque(maxlen=250)

    def _transport_info(self, packet):
        src_ip, dst_ip = "N/A", "N/A"
        src_port, dst_port = "N/A", "N/A"
        network_protocol = "UNKNOWN"

        if ARP in packet:
            network_protocol = "ARP"
            src_ip = packet[ARP].psrc
            dst_ip = packet[ARP].pdst
        elif IP in packet:
            src_ip = packet[IP].src
            dst_ip = packet[IP].dst
            if TCP in packet:
                src_port = packet[TCP].sport
                dst_port = packet[TCP].dport
                network_protocol = "TCP"
            elif UDP in packet:
                src_port = packet[UDP].sport
                dst_port = packet[UDP].dport
                network_protocol = "UDP"
            else:
                network_protocol = f"IP_PROTO_{packet[IP].proto}"
        elif IPv6 in packet:
            src_ip = packet[IPv6].src
            dst_ip = packet[IPv6].dst
            if TCP in packet:
                src_port = packet[TCP].sport
                dst_port = packet[TCP].dport
                network_protocol = "TCPv6"
            elif UDP in packet:
                src_port = packet[UDP].sport
                dst_port = packet[UDP].dport
                network_protocol = "UDPv6"
            else:
                network_protocol = f"IPv6_PROTO_{packet[IPv6].nh}"
        elif Ether in packet:
            network_protocol = hex(packet[Ether].type)

        return src_ip, dst_ip, src_port, dst_port, network_protocol

    def _payload_bytes(self, packet):
        if Raw in packet:
            try:
                return bytes(packet[Raw].load)
            except Exception:
                return b""
        return b""

    def _parse_http(self, payload_text):
        parsed = {
            "http_method": "",
            "http_path": "",
            "http_version": "",
            "http_status": "",
            "http_reason": "",
            "http_headers": {},
            "http_host": "",
            "user_agent": "",
            "content_type": "",
            "content_length": "",
        }

        if not payload_text:
            return parsed

        lines = payload_text.split("\n")
        first_line = lines[0].strip() if lines else ""

        request_match = HTTP_METHOD_RE.match(first_line)
        if request_match:
            parsed["http_method"] = request_match.group(1).upper()
            parsed["http_path"] = request_match.group(2)
            parsed["http_version"] = request_match.group(3)
        else:
            status_match = HTTP_STATUS_RE.match(first_line)
            if status_match:
                parsed["http_version"] = status_match.group(1)
                parsed["http_status"] = status_match.group(2)
                parsed["http_reason"] = status_match.group(3).strip()

        for raw_line in lines[1:]:
            line = raw_line.strip("\r").strip()
            if not line:
                break
            header_match = HEADER_RE.match(line)
            if not header_match:
                continue
            key = header_match.group(1).strip().lower()
            value = header_match.group(2).strip()
            parsed["http_headers"][key] = value

        parsed["http_host"] = parsed["http_headers"].get("host", "")
        parsed["user_agent"] = parsed["http_headers"].get("user-agent", "")
        parsed["content_type"] = parsed["http_headers"].get("content-type", "")
        parsed["content_length"] = parsed["http_headers"].get("content-length", "")
        return parsed

    def _parse_dns(self, packet):
        if DNS is None or not packet.haslayer(DNS):
            return {"dns_query": "", "dns_type": "", "dns_response": ""}

        dns_layer = packet[DNS]
        result = {"dns_query": "", "dns_type": "", "dns_response": ""}

        try:
            if getattr(dns_layer, "qdcount", 0) and packet.haslayer(DNSQR):
                query = packet[DNSQR]
                result["dns_query"] = _safe_text(getattr(query, "qname", b""))
                result["dns_type"] = str(getattr(query, "qtype", ""))
            if getattr(dns_layer, "ancount", 0):
                result["dns_response"] = str(getattr(dns_layer, "ancount", 0))
        except Exception:
            pass

        return result

    def _parse_tls_sni(self, packet):
        if TLS is None or TLSClientHello is None:
            return ""

        try:
            if not packet.haslayer(TLSClientHello):
                return ""

            hello = packet[TLSClientHello]
            extensions = getattr(hello, "ext", None) or getattr(hello, "extensions", None) or []
            for ext in extensions:
                if hasattr(ext, "servernames"):
                    servernames = getattr(ext, "servernames", []) or []
                    for servername in servernames:
                        name = getattr(servername, "servername", b"")
                        if name:
                            return _safe_text(name)
                if "ServerName" in ext.__class__.__name__ and hasattr(ext, "servername"):
                    name = getattr(ext, "servername", b"")
                    if name:
                        return _safe_text(name)
        except Exception:
            return ""

        return ""

    def extract_packet_data(self, packet, local_ip=None):
        src_ip, dst_ip, src_port, dst_port, network_protocol = self._transport_info(packet)
        payload = self._payload_bytes(packet)
        payload_text = _safe_text(payload)
        http_data = self._parse_http(payload_text)
        dns_data = self._parse_dns(packet)
        tls_sni = self._parse_tls_sni(packet)
        src_domain = _reverse_dns(src_ip)
        dst_domain = _reverse_dns(dst_ip)

        application_domain = ""
        if http_data["http_host"]:
            application_domain = http_data["http_host"]
        elif tls_sni:
            application_domain = tls_sni
        elif dns_data["dns_query"]:
            application_domain = dns_data["dns_query"]

        if http_data["http_method"]:
            application_protocol = "HTTP"
        elif dns_data["dns_query"]:
            application_protocol = "DNS"
        elif tls_sni or dst_port in {443, 8443, 9443} or src_port in {443, 8443, 9443}:
            application_protocol = "TLS"
        elif dst_port in {80, 8080, 8000, 8888, 5000} or src_port in {80, 8080, 8000, 8888, 5000}:
            application_protocol = "HTTP"
        else:
            application_protocol = network_protocol

        direction = "unknown"
        if local_ip and src_ip == local_ip:
            direction = "outgoing"
        elif local_ip and dst_ip == local_ip:
            direction = "incoming"

        packet_data = {
            "timestamp": datetime.now().isoformat(),
            "src_ip": src_ip,
            "dst_ip": dst_ip,
            "src_port": src_port,
            "dst_port": dst_port,
            "protocol": network_protocol,
            "application_protocol": application_protocol,
            "direction": direction,
            "src_domain": src_domain,
            "dst_domain": dst_domain,
            "application_domain": application_domain,
            "packet_size": len(bytes(packet)),
            "payload_length": len(payload),
            "payload": payload_text,
            "payload_preview": payload_text[:512],
            "payload_hex_preview": _safe_hex_preview(payload),
            "http_method": http_data["http_method"],
            "http_path": http_data["http_path"],
            "http_version": http_data["http_version"],
            "http_status": http_data["http_status"],
            "http_reason": http_data["http_reason"],
            "http_host": http_data["http_host"],
            "http_headers": http_data["http_headers"],
            "user_agent": http_data["user_agent"],
            "content_type": http_data["content_type"],
            "content_length": http_data["content_length"],
            "dns_query": dns_data["dns_query"],
            "dns_type": dns_data["dns_type"],
            "dns_response": dns_data["dns_response"],
            "tls_sni": tls_sni,
        }

        return packet_data

    def inspect_packet(self, packet, local_ip=None):
        packet_data = self.extract_packet_data(packet, local_ip=local_ip)

        with self.lock:
            self.packet_count += 1
            if packet_data.get("payload_length", 0) > 0:
                self.payload_packet_count += 1
            self.application_counts[packet_data["application_protocol"]] += 1
            self.protocol_counts[packet_data["protocol"]] += 1
            self.recent_packets.append(packet_data)

        alerts = []
        if self.rule_engine:
            try:
                alerts = self.rule_engine.evaluate_packet(packet_data) or []
            except Exception as exc:
                print(f"[DPI] Rule evaluation error: {exc}")
                alerts = []

        if alerts:
            with self.lock:
                for alert in alerts:
                    enriched = dict(alert)
                    enriched.setdefault("inspection_type", "dpi")
                    enriched.setdefault("packet_data", packet_data)
                    self.alerts.append(enriched)
                self.alerts = self.alerts[-1000:]

        return packet_data, alerts

    def get_alerts(self, limit=100):
        with self.lock:
            return list(self.alerts[-limit:])

    def get_recent_packets(self, limit=25):
        with self.lock:
            return list(self.recent_packets)[-limit:]

    def get_statistics(self):
        with self.lock:
            return {
                "total_packets": self.packet_count,
                "packets_with_payload": self.payload_packet_count,
                "recent_alerts": len(self.alerts),
                "protocol_counts": dict(self.protocol_counts),
                "application_protocol_counts": dict(self.application_counts),
            }


_dpi_engine = None


def get_dpi_engine():
    global _dpi_engine
    if _dpi_engine is None:
        _dpi_engine = DPIEngine()
    return _dpi_engine


def inspect_packet(packet, local_ip=None):
    return get_dpi_engine().inspect_packet(packet, local_ip=local_ip)
