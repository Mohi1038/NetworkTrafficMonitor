"""
GeoIP Mapping Module - Real-time geographic location of network traffic
Uses MaxMind GeoLite2 and free IP-API for location data
"""

import requests
import json
import os
from pathlib import Path
from datetime import datetime, timedelta
from collections import defaultdict
import threading

# Cache directory for IP locations
CACHE_DIR = Path(os.environ.get("NTM_CACHE_DIR", Path(__file__).parent / ".ntm_cache"))
CACHE_DIR.mkdir(exist_ok=True)
CACHE_FILE = CACHE_DIR / "geoip_cache.json"
CACHE_DURATION = 86400  # 24 hours

class GeoIPMapper:
    """Map IPs to geographic locations"""
    
    def __init__(self):
        self.cache = self._load_cache()
        self.lock = threading.Lock()
        self.failed_ips = set()  # Track IPs that failed lookup
        self.lookup_count = 0
        
    def _load_cache(self):
        """Load cached IP-to-location mappings"""
        try:
            if CACHE_FILE.exists():
                with open(CACHE_FILE, 'r') as f:
                    return json.load(f)
        except Exception as e:
            print(f"[GeoIP] Cache load error: {e}")
        return {}
    
    def _save_cache(self):
        """Persist cache to disk"""
        try:
            with open(CACHE_FILE, 'w') as f:
                json.dump(self.cache, f)
        except Exception as e:
            print(f"[GeoIP] Cache save error: {e}")
    
    def get_location(self, ip_address, use_cache=True):
        """
        Get geographic location for an IP address
        
        Args:
            ip_address: IP address to lookup
            use_cache: Whether to use cached results
            
        Returns:
            dict with: country, city, lat, lon, org, threat_level
        """
        
        if not ip_address or ip_address.startswith("127.") or ip_address.startswith("192.168."):
            return self._local_ip_location()
        
        # Check cache first
        if use_cache and ip_address in self.cache:
            cached = self.cache[ip_address]
            if datetime.fromisoformat(cached['cached_at']) > (datetime.now() - timedelta(seconds=CACHE_DURATION)):
                return cached['data']
        
        # Skip failed lookups for this session
        if ip_address in self.failed_ips:
            return self._unknown_location(ip_address)
        
        # Try lookup (free service)
        location = self._lookup_ip(ip_address)
        
        if location and location.get('country'):
            # Cache successful lookup
            with self.lock:
                self.cache[ip_address] = {
                    'data': location,
                    'cached_at': datetime.now().isoformat()
                }
                self.lookup_count += 1
                if self.lookup_count % 10 == 0:
                    self._save_cache()
            return location
        else:
            # Track failed lookup
            self.failed_ips.add(ip_address)
            return self._unknown_location(ip_address)
    
    def _lookup_ip(self, ip_address):
        """Lookup IP using free service (ip-api.com)"""
        try:
            # Using free tier of ip-api.com (45 req/min limit)
            url = f"http://ip-api.com/json/{ip_address}?fields=status,country,city,lat,lon,org,query"
            response = requests.get(url, timeout=2)
            
            if response.status_code == 200:
                data = response.json()
                if data.get('status') == 'success':
                    return {
                        'ip': ip_address,
                        'country': data.get('country', 'Unknown'),
                        'city': data.get('city', 'Unknown'),
                        'latitude': float(data.get('lat', 0)),
                        'longitude': float(data.get('lon', 0)),
                        'organization': data.get('org', 'Unknown'),
                        'threat_level': 'low'  # Can be enhanced with threat intelligence
                    }
        except Exception as e:
            print(f"[GeoIP] Lookup failed for {ip_address}: {e}")
        
        return None
    
    def _local_ip_location(self):
        """Return location for local IPs"""
        return {
            'ip': 'Local',
            'country': 'Local Network',
            'city': 'Your Network',
            'latitude': 0,
            'longitude': 0,
            'organization': 'Local',
            'threat_level': 'low'
        }
    
    def _unknown_location(self, ip_address):
        """Return unknown location"""
        return {
            'ip': ip_address,
            'country': 'Unknown',
            'city': 'Unknown',
            'latitude': 0,
            'longitude': 0,
            'organization': 'Unknown',
            'threat_level': 'unknown'
        }
    
    def get_traffic_map_data(self, traffic_table):
        """
        Convert traffic table to geo-map data
        
        Args:
            traffic_table: List of traffic records
            
        Returns:
            List of geo-located traffic points
        """
        geo_data = []
        
        for entry in traffic_table[:100]:  # Limit to top 100
            src_ip = entry.get('src_ip', '')
            dst_ip = entry.get('dst_ip', '')
            size = entry.get('size', 0)
            
            # Get location for source IP
            src_location = self.get_location(src_ip)
            
            geo_data.append({
                'source_ip': src_ip,
                'destination_ip': dst_ip,
                'size': size,
                'protocol': entry.get('protocol', 'Unknown'),
                'location': src_location,
                'timestamp': entry.get('timestamp', '')
            })
        
        return geo_data

# Global instance
_geoip_mapper = None

def get_geoip_mapper():
    """Get or create global GeoIP mapper instance"""
    global _geoip_mapper
    if _geoip_mapper is None:
        _geoip_mapper = GeoIPMapper()
    return _geoip_mapper

def get_ip_location(ip_address):
    """Convenience function to get location for an IP"""
    mapper = get_geoip_mapper()
    return mapper.get_location(ip_address)

def get_map_data(traffic_table):
    """Convenience function to get map data"""
    mapper = get_geoip_mapper()
    return mapper.get_traffic_map_data(traffic_table)
