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


_domain_cache = {}  # IP -> domain mapping
_dns_query_cache = {}  # Domain -> IPs from DNS queries
_alias_map = {}  # Hostname alias -> canonical domain (e.g., CDN host -> youtube.com)
_canonical_host_map = {
    "googlevideo.com": "youtube.com",
    "1e100.net": "google.com",
    "ytimg.com": "youtube.com",
}


def _is_ip_address(text):
    """Check if text is a valid IPv4 or IPv6 address."""
    if not text:
        return False
    try:
        socket.inet_pton(socket.AF_INET, text)
        return True
    except (socket.error, OSError, TypeError):
        pass
    try:
        socket.inet_pton(socket.AF_INET6, text)
        return True
    except (socket.error, OSError, TypeError):
        pass
    return False


def _reverse_dns(ip_address):
    """Get domain for IP from cache, reverse DNS, or DNS query history."""
    if not ip_address or ip_address in {"N/A", "unknown"}:
        return ""
    if ip_address in _domain_cache:
        return _domain_cache[ip_address]

    # Try reverse DNS
    try:
        hostname = socket.gethostbyaddr(ip_address)[0]
        _domain_cache[ip_address] = hostname
        return hostname
    except Exception:
        pass
    
    # Try DNS query history - look for this IP in our DNS cache
    for domain, ips in _dns_query_cache.items():
        if ip_address in ips:
            _domain_cache[ip_address] = domain
            return domain
    
    return ""


def _cache_dns_mapping(domain, ips):
    """Cache DNS query results to map domains to IPs."""
    if not domain or not ips:
        return
    _dns_query_cache[domain] = ips
    # Also cache the reverse mapping
    for ip in ips:
        if not _domain_cache.get(ip):
            _domain_cache[ip] = domain


def _cache_alias_mapping(alias, canonical):
    """Cache a hostname alias (CNAME) to a canonical domain name."""
    try:
        if not alias or not canonical:
            return
        a = alias.rstrip('.').lower()
        c = canonical.rstrip('.').lower()
        # Prefer existing canonical mapping if already present
        _alias_map[a] = c
    except Exception:
        pass


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
        """Extract DNS queries and responses like Wireshark does."""
        if DNS is None:
            return {"dns_query": "", "dns_type": "", "dns_response": ""}

        if not packet.haslayer(DNS):
            return {"dns_query": "", "dns_type": "", "dns_response": ""}

        dns_layer = packet[DNS]
        result = {"dns_query": "", "dns_type": "", "dns_response": ""}

        try:
            # Extract DNS query from DNSQR layer
            if DNSQR and packet.haslayer(DNSQR):
                dnsqr = packet[DNSQR]
                qname = getattr(dnsqr, 'qname', b"")
                if qname:
                    # Decode and clean up domain name
                    if isinstance(qname, bytes):
                        domain = qname.decode('utf-8', errors='ignore').rstrip('.')
                    else:
                        domain = str(qname).rstrip('.')
                    result["dns_query"] = domain
                    
                    # Get query type if available
                    qtype = getattr(dnsqr, 'qtype', 'A')
                    result["dns_type"] = str(qtype) if qtype else "A"
            
            # Extract DNS responses and cache the mapping
            if getattr(dns_layer, "ancount", 0) > 0 and result["dns_query"]:
                result["dns_response"] = str(getattr(dns_layer, "ancount", 0))
                
                # Extract response IPs from answer records
                response_ips = []
                try:
                    # Get the answer layer
                    an = getattr(dns_layer, 'an', None)
                    if an:
                        # an might be a single answer or multiple chained
                        current = an
                        while current:
                            # Try to get the RDATA
                            if hasattr(current, 'rdata'):
                                ip_str = str(current.rdata).strip()
                            else:
                                ip_str = str(current).strip()
                            
                            # Only include valid IP addresses
                            if ip_str and ip_str not in {'N/A', 'unknown', '0.0.0.0', '::'}:
                                if _is_ip_address(ip_str):
                                    response_ips.append(ip_str)
                                else:
                                    # Non-IP RDATA may be a CNAME/alias (e.g., cdn host)
                                    # Cache alias -> original query mapping so we can
                                    # display the canonical domain later (e.g., youtube.com)
                                    try:
                                        alias = ip_str.rstrip('.')
                                        _cache_alias_mapping(alias, result["dns_query"])
                                    except Exception:
                                        pass
                            
                            # Move to next answer record
                            current = getattr(current, 'payload', None) if hasattr(current, 'payload') else None
                except Exception:
                    pass
                
                # Cache the domain->IP mapping for future lookups
                if response_ips and result["dns_query"]:
                    _cache_dns_mapping(result["dns_query"], response_ips)
        except Exception:
            pass

        return result

    def _parse_tls_sni(self, packet):
        """Extract TLS SNI (Server Name Indication) like Wireshark does."""
        if TLS is None:
            # Fallback: try to extract SNI from raw TLS ClientHello packet data
            return self._extract_sni_from_raw(packet)

        try:
            # Try Scapy's TLS layer parsing
            if packet.haslayer(TLS):
                tls_layer = packet[TLS]
                
                # Look for ClientHello
                if hasattr(tls_layer, 'handshakes'):
                    for handshake in tls_layer.handshakes:
                        if hasattr(handshake, 'client_hello'):
                            ch = handshake.client_hello
                            if hasattr(ch, 'extensions'):
                                for ext in ch.extensions:
                                    if hasattr(ext, 'server_name'):
                                        return str(ext.server_name).strip()
                
                # Alternative: check for TLSClientHello directly
                if TLSClientHello and packet.haslayer(TLSClientHello):
                    hello = packet[TLSClientHello]
                    
                    # Try various ways to access extensions
                    extensions = None
                    if hasattr(hello, 'ext'):
                        extensions = hello.ext
                    elif hasattr(hello, 'extensions'):
                        extensions = hello.extensions
                    
                    if extensions:
                        if isinstance(extensions, list):
                            for ext in extensions:
                                sni = self._extract_sni_from_extension(ext)
                                if sni:
                                    return sni
                        else:
                            sni = self._extract_sni_from_extension(extensions)
                            if sni:
                                return sni
        except Exception:
            pass

        # Fallback to raw packet data extraction
        return self._extract_sni_from_raw(packet)

    def _extract_sni_from_extension(self, ext):
        """Extract SNI from a TLS extension object."""
        try:
            # Check various attribute names
            if hasattr(ext, "servernames"):
                servernames = ext.servernames or []
                for sn in servernames:
                    if hasattr(sn, "servername"):
                        name = getattr(sn, "servername", b"")
                        if name:
                            if isinstance(name, bytes):
                                return name.decode('utf-8', errors='ignore').strip()
                            return str(name).strip()
            
            if hasattr(ext, "servername"):
                name = ext.servername
                if name:
                    if isinstance(name, bytes):
                        return name.decode('utf-8', errors='ignore').strip()
                    return str(name).strip()
            
            if hasattr(ext, "server_name"):
                name = ext.server_name
                if name:
                    if isinstance(name, bytes):
                        return name.decode('utf-8', errors='ignore').strip()
                    return str(name).strip()
        except Exception:
            pass
        
        return ""

    def _extract_sni_from_raw(self, packet):
        """Extract SNI from raw TLS ClientHello packet data."""
        try:
            if Raw not in packet:
                return ""
            
            payload = bytes(packet[Raw].load)
            if len(payload) < 50:
                return ""
            
            # TLS record: skip first 5 bytes (type, version, length)
            # Then find the ClientHello and look for SNI extension
            # This is a simplified extraction - just look for domain-like strings
            # after the TLS handshake start
            
            # Look for the server_name extension (type 0x0000)
            sni_marker = b'\x00\x00'  # Extension type for server_name
            
            # Find SNI extension in the payload
            idx = payload.find(sni_marker)
            if idx > 0 and idx < len(payload) - 10:
                # Skip the extension type and length bytes
                # Extract length (2 bytes) and then the SNI list length (2 bytes)
                try:
                    ext_len = int.from_bytes(payload[idx+2:idx+4], 'big')
                    sni_list_len = int.from_bytes(payload[idx+4:idx+6], 'big')
                    name_type = payload[idx+6]  # 0 = host_name
                    
                    if name_type == 0 and idx + 9 < len(payload):
                        name_len = int.from_bytes(payload[idx+7:idx+9], 'big')
                        if name_len > 0 and name_len < 256:
                            domain = payload[idx+9:idx+9+name_len].decode('utf-8', errors='ignore')
                            return domain.strip()
                except Exception:
                    pass
        except Exception:
            pass
        
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
        
        # Enhanced domain detection: use application-layer data (HTTP Host, TLS SNI) as fallback
        # For outgoing connections: destination domain should be the SNI/Host (what we're connecting to)
        # For incoming connections: source domain should be the SNI/Host (who's sending to us)
        determined_direction = "unknown"
        if local_ip and src_ip == local_ip:
            determined_direction = "outgoing"
        elif local_ip and dst_ip == local_ip:
            determined_direction = "incoming"
        
        if not dst_domain and (http_data["http_host"] or tls_sni) and determined_direction == "outgoing":
            # For outgoing: we want to know what website we're visiting
            dst_domain = http_data["http_host"] or tls_sni or dst_domain
        
        if not src_domain and (http_data["http_host"] or tls_sni) and determined_direction == "incoming":
            # For incoming: we want to know what server is sending to us
            src_domain = http_data["http_host"] or tls_sni or src_domain

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

        # Use the direction we already determined
        direction = determined_direction

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

        # Normalize domains using alias map (map CDN hostnames back to canonical domains)
        try:
            if packet_data.get('application_domain'):
                ad = packet_data['application_domain'].rstrip('.').lower()
                if ad in _alias_map:
                    packet_data['application_domain'] = _alias_map[ad]
            if packet_data.get('dst_domain'):
                dd = packet_data['dst_domain'].rstrip('.').lower()
                if dd in _alias_map:
                    packet_data['dst_domain'] = _alias_map[dd]
            if packet_data.get('src_domain'):
                sd = packet_data['src_domain'].rstrip('.').lower()
                if sd in _alias_map:
                    packet_data['src_domain'] = _alias_map[sd]
        except Exception:
            pass

        # Heuristic canonicalization: map known CDN host suffixes to user-friendly domains
        try:
            def _apply_canonical(name):
                if not name:
                    return name
                ln = name.lower()
                for suffix, canon in _canonical_host_map.items():
                    if suffix in ln:
                        return canon
                return name

            packet_data['application_domain'] = _apply_canonical(packet_data.get('application_domain', ''))
            packet_data['dst_domain'] = _apply_canonical(packet_data.get('dst_domain', ''))
            packet_data['src_domain'] = _apply_canonical(packet_data.get('src_domain', ''))
        except Exception:
            pass

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
