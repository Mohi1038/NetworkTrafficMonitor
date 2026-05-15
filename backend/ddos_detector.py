"""
DDoS Attack Detection Module
Detects patterns indicative of Distributed Denial of Service attacks
"""

from collections import defaultdict, deque
from datetime import datetime, timedelta
import threading
import math

class DDosDetector:
    """Detect DDoS attack patterns in network traffic"""
    
    def __init__(self):
        # Configuration thresholds
        self.SYN_FLOOD_THRESHOLD = 100  # SYN packets per second
        self.CONNECTION_RATE_THRESHOLD = 50  # New connections per second
        self.PACKET_RATE_THRESHOLD = 1000  # Packets per second
        self.ENTROPY_THRESHOLD = 3.0  # Source IP entropy threshold
        self.DETECTION_WINDOW = 10  # Seconds
        
        # Tracking structures
        self.syn_packets = defaultdict(deque)  # {dst_ip: deque of timestamps}
        self.connections = defaultdict(deque)  # {dst_ip: deque of timestamps}
        self.packets = defaultdict(deque)  # {dst_ip: deque of timestamps}
        self.source_ips = defaultdict(set)  # {dst_ip: set of source IPs}
        
        self.alerts = []  # List of DDoS alerts
        self.lock = threading.Lock()
        self.attack_history = defaultdict(lambda: {'start': None, 'severity': 0})
    
    def detect_syn_flood(self, dst_ip, is_syn_packet=False):
        """Detect SYN flood attacks"""
        if not is_syn_packet:
            return None
        
        now = datetime.now()
        window_start = now - timedelta(seconds=self.DETECTION_WINDOW)
        
        with self.lock:
            # Add packet timestamp
            self.syn_packets[dst_ip].append(now)
            
            # Remove old entries
            while self.syn_packets[dst_ip] and self.syn_packets[dst_ip][0] < window_start:
                self.syn_packets[dst_ip].popleft()
            
            # Count SYN packets in window
            syn_count = len(self.syn_packets[dst_ip])
            syn_rate = syn_count / self.DETECTION_WINDOW
            
            # Detect SYN flood
            if syn_rate > self.SYN_FLOOD_THRESHOLD:
                severity = min(100, int((syn_rate / self.SYN_FLOOD_THRESHOLD) * 100))
                alert = {
                    'type': 'SYN_FLOOD',
                    'dst_ip': dst_ip,
                    'severity': severity,
                    'metric': f'{syn_rate:.0f} SYN/sec',
                    'timestamp': now.isoformat(),
                    'details': f'Detected SYN flood: {syn_rate:.0f} packets/sec (threshold: {self.SYN_FLOOD_THRESHOLD})'
                }
                return alert
        
        return None
    
    def detect_connection_flood(self, dst_ip):
        """Detect connection flood attacks"""
        now = datetime.now()
        window_start = now - timedelta(seconds=self.DETECTION_WINDOW)
        
        with self.lock:
            # Add connection timestamp
            self.connections[dst_ip].append(now)
            
            # Remove old entries
            while self.connections[dst_ip] and self.connections[dst_ip][0] < window_start:
                self.connections[dst_ip].popleft()
            
            # Count connections in window
            conn_count = len(self.connections[dst_ip])
            conn_rate = conn_count / self.DETECTION_WINDOW
            
            # Detect connection flood
            if conn_rate > self.CONNECTION_RATE_THRESHOLD:
                severity = min(100, int((conn_rate / self.CONNECTION_RATE_THRESHOLD) * 100))
                alert = {
                    'type': 'CONNECTION_FLOOD',
                    'dst_ip': dst_ip,
                    'severity': severity,
                    'metric': f'{conn_rate:.0f} conn/sec',
                    'timestamp': now.isoformat(),
                    'details': f'Connection flood detected: {conn_rate:.0f} conn/sec (threshold: {self.CONNECTION_RATE_THRESHOLD})'
                }
                return alert
        
        return None
    
    def detect_packet_flood(self, dst_ip, packet_size=0):
        """Detect volumetric (packet flood) attacks"""
        now = datetime.now()
        window_start = now - timedelta(seconds=self.DETECTION_WINDOW)
        
        with self.lock:
            # Add packet timestamp
            self.packets[dst_ip].append((now, packet_size))
            
            # Remove old entries
            while self.packets[dst_ip] and self.packets[dst_ip][0][0] < window_start:
                self.packets[dst_ip].popleft()
            
            # Count packets in window
            pkt_count = len(self.packets[dst_ip])
            pkt_rate = pkt_count / self.DETECTION_WINDOW
            
            # Calculate volume (bytes per second)
            volume = sum(size for _, size in self.packets[dst_ip])
            mbps = (volume * 8) / (self.DETECTION_WINDOW * 1_000_000)
            
            # Detect packet flood
            if pkt_rate > self.PACKET_RATE_THRESHOLD:
                severity = min(100, int((pkt_rate / self.PACKET_RATE_THRESHOLD) * 100))
                alert = {
                    'type': 'PACKET_FLOOD',
                    'dst_ip': dst_ip,
                    'severity': severity,
                    'metric': f'{pkt_rate:.0f} pkt/sec, {mbps:.1f} Mbps',
                    'timestamp': now.isoformat(),
                    'details': f'Volumetric attack: {pkt_rate:.0f} packets/sec, {mbps:.1f} Mbps (threshold: {self.PACKET_RATE_THRESHOLD} pkt/sec)'
                }
                return alert
        
        return None
    
    def detect_distributed_attack(self, dst_ip, src_ip):
        """Detect distributed attacks (multiple source IPs)"""
        now = datetime.now()
        
        with self.lock:
            # Track source IPs
            self.source_ips[dst_ip].add(src_ip)
            
            unique_sources = len(self.source_ips[dst_ip])
            
            # If many different sources targeting same destination = distributed
            if unique_sources > 50:
                severity = min(100, int((unique_sources / 100) * 100))
                alert = {
                    'type': 'DISTRIBUTED_ATTACK',
                    'dst_ip': dst_ip,
                    'severity': severity,
                    'metric': f'{unique_sources} source IPs',
                    'timestamp': now.isoformat(),
                    'details': f'Distributed attack detected from {unique_sources} unique source IPs'
                }
                return alert
        
        return None
    
    def process_packet(self, src_ip, dst_ip, packet_size=0, flags=None):
        """
        Process a packet and check for DDoS patterns
        
        Args:
            src_ip: Source IP address
            dst_ip: Destination IP address
            packet_size: Size of packet in bytes
            flags: TCP flags (for SYN detection)
            
        Returns:
            DDoS alert dict if detected, None otherwise
        """
        alerts = []
        
        # Check for SYN flood (TCP SYN flag)
        is_syn = flags and (flags & 0x02)  # SYN flag
        if is_syn:
            alert = self.detect_syn_flood(dst_ip, is_syn_packet=True)
            if alert:
                alerts.append(alert)
        
        # Check for connection flood
        alert = self.detect_connection_flood(dst_ip)
        if alert:
            alerts.append(alert)
        
        # Check for packet flood
        alert = self.detect_packet_flood(dst_ip, packet_size)
        if alert:
            alerts.append(alert)
        
        # Check for distributed attack
        alert = self.detect_distributed_attack(dst_ip, src_ip)
        if alert:
            alerts.append(alert)
        
        # Store alerts
        if alerts:
            with self.lock:
                self.alerts.extend(alerts)
                # Keep only last 1000 alerts
                self.alerts = self.alerts[-1000:]
        
        return alerts[0] if alerts else None
    
    def get_alerts(self, limit=50):
        """Get recent DDoS alerts"""
        with self.lock:
            return self.alerts[-limit:]
    
    def clear_alerts(self):
        """Clear alert history"""
        with self.lock:
            self.alerts.clear()
    
    def get_statistics(self):
        """Get DDoS detection statistics"""
        with self.lock:
            total_alerts = len(self.alerts)
            alert_types = defaultdict(int)
            
            for alert in self.alerts:
                alert_types[alert['type']] += 1
            
            return {
                'total_alerts': total_alerts,
                'alert_types': dict(alert_types),
                'tracked_destinations': len(self.packets),
                'max_sources': max([len(ips) for ips in self.source_ips.values()]) if self.source_ips else 0
            }

# Global instance
_ddos_detector = None

def get_ddos_detector():
    """Get or create global DDoS detector"""
    global _ddos_detector
    if _ddos_detector is None:
        _ddos_detector = DDosDetector()
    return _ddos_detector

def detect_ddos(src_ip, dst_ip, packet_size=0, flags=None):
    """Convenience function to detect DDoS attacks"""
    detector = get_ddos_detector()
    return detector.process_packet(src_ip, dst_ip, packet_size, flags)
