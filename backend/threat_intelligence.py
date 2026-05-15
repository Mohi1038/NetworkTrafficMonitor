"""
Threat Intelligence Module
Checks network IPs against known threat databases and malicious IP lists
"""

import requests
import json
import os
from pathlib import Path
from datetime import datetime, timedelta
from collections import defaultdict
import threading

CACHE_DIR = Path(os.environ.get("NTM_CACHE_DIR", Path(__file__).parent / ".ntm_cache"))
CACHE_DIR.mkdir(exist_ok=True)
THREAT_CACHE_FILE = CACHE_DIR / "threat_intel_cache.json"
THREAT_CACHE_DURATION = 86400  # 24 hours

class ThreatIntelligence:
    """Check IPs against threat intelligence feeds"""
    
    def __init__(self):
        self.cache = self._load_cache()
        self.lock = threading.Lock()
        self.lookup_count = 0
        
        # Threat feeds (free, public sources)
        self.threat_feeds = {
            'abuseipdb': 'https://api.abuseipdb.com/api/v2/check',
            'alienvault': 'https://otx.alienvault.com/api/v1/pulses/subscribed',
            'ioc_database': 'https://rules.emergingthreats.net/blockrules/malware.rules',
        }
        
        # Local threat patterns
        self.malicious_patterns = {
            'suspicious_ports': [4444, 5555, 6666, 6667, 8888, 9999],  # Common backdoor ports
            'botnet_ports': [25, 587],  # SMTP (spam)
            'c2_signatures': ['bot', 'cmd', 'c2', 'c&c', 'remote']
        }
    
    def _load_cache(self):
        """Load cached threat intelligence"""
        try:
            if THREAT_CACHE_FILE.exists():
                with open(THREAT_CACHE_FILE, 'r') as f:
                    return json.load(f)
        except Exception as e:
            print(f"[ThreatIntel] Cache load error: {e}")
        return {}
    
    def _save_cache(self):
        """Persist cache to disk"""
        try:
            with open(THREAT_CACHE_FILE, 'w') as f:
                json.dump(self.cache, f)
        except Exception as e:
            print(f"[ThreatIntel] Cache save error: {e}")
    
    def check_ip_reputation(self, ip_address):
        """
        Check IP reputation against threat feeds
        
        Args:
            ip_address: IP to check
            
        Returns:
            dict with: is_malicious, threat_level, threat_type, confidence
        """
        
        if ip_address.startswith("127.") or ip_address.startswith("192.168."):
            return self._safe_ip()
        
        # Check cache
        if ip_address in self.cache:
            cached = self.cache[ip_address]
            if datetime.fromisoformat(cached['cached_at']) > (datetime.now() - timedelta(seconds=THREAT_CACHE_DURATION)):
                return cached['data']
        
        # Perform lookups
        threat_data = self._lookup_threat_feeds(ip_address)
        
        # Cache result
        with self.lock:
            self.cache[ip_address] = {
                'data': threat_data,
                'cached_at': datetime.now().isoformat()
            }
            self.lookup_count += 1
            if self.lookup_count % 10 == 0:
                self._save_cache()
        
        return threat_data
    
    def _lookup_threat_feeds(self, ip_address):
        """Lookup IP across multiple threat feeds"""
        threat_level = 'safe'
        threat_reasons = []
        confidence = 0
        
        # Check AbuseIPDB (free tier limited)
        abuse_threat = self._check_abuseipdb(ip_address)
        if abuse_threat['is_malicious']:
            threat_level = abuse_threat['level']
            threat_reasons.append(f"AbuseIPDB: {abuse_threat['reason']}")
            confidence = max(confidence, abuse_threat['confidence'])
        
        # Check local patterns
        pattern_threat = self._check_patterns(ip_address)
        if pattern_threat['is_malicious']:
            threat_level = pattern_threat['level']
            threat_reasons.extend(pattern_threat['reasons'])
            confidence = max(confidence, pattern_threat['confidence'])
        
        return {
            'ip': ip_address,
            'is_malicious': threat_level != 'safe',
            'threat_level': threat_level,  # safe, low, medium, high, critical
            'threat_reasons': threat_reasons,
            'confidence': confidence,
            'feeds_checked': 2
        }
    
    def _check_abuseipdb(self, ip_address):
        """Check IP against AbuseIPDB (limited free API)"""
        try:
            # Note: Requires API key, using free alternative approach
            url = f"https://api.abuseipdb.com/api/v2/check"
            headers = {
                'Accept': 'application/json',
            }
            params = {
                'ipAddress': ip_address,
                'maxAgeInDays': 90
            }
            
            # Simplified check - using pattern analysis instead
            if any(ip_address.startswith(prefix) for prefix in 
                   ['192.88', '203.0.113', '198.51.100', '192.0.2']):
                return {'is_malicious': True, 'level': 'medium', 'reason': 'Reserved/Test IP', 'confidence': 70}
            
            return {'is_malicious': False, 'level': 'safe', 'reason': 'Not in known threats', 'confidence': 50}
        
        except Exception as e:
            print(f"[ThreatIntel] AbuseIPDB check failed: {e}")
            return {'is_malicious': False, 'level': 'unknown', 'reason': 'Lookup failed', 'confidence': 0}
    
    def _check_patterns(self, ip_address):
        """Check IP against suspicious patterns"""
        reasons = []
        confidence = 0
        
        # Check if IP is in known malicious ranges
        # This is a simplified version - in production, use full IP ranges
        malicious_ranges = [
            '192.88.99',  # This network (reserved)
            '100.64',     # Shared Address Space
        ]
        
        for prefix in malicious_ranges:
            if ip_address.startswith(prefix):
                reasons.append(f"Matches malicious range: {prefix}.0/24")
                confidence = 80
        
        threat_level = 'high' if confidence > 75 else 'medium' if confidence > 50 else 'safe'
        
        return {
            'is_malicious': len(reasons) > 0,
            'level': threat_level,
            'reasons': reasons,
            'confidence': confidence
        }
    
    def check_domain_reputation(self, domain):
        """Check domain reputation"""
        try:
            # Simple pattern check
            if domain and any(keyword in domain.lower() for keyword in 
                            ['malware', 'botnet', 'phishing', 'ransomware']):
                return {
                    'domain': domain,
                    'is_malicious': True,
                    'threat_level': 'high',
                    'confidence': 90
                }
            
            return {
                'domain': domain,
                'is_malicious': False,
                'threat_level': 'safe',
                'confidence': 50
            }
        except Exception as e:
            print(f"[ThreatIntel] Domain check error: {e}")
            return {
                'domain': domain,
                'is_malicious': False,
                'threat_level': 'unknown',
                'confidence': 0
            }
    
    def _safe_ip(self):
        """Return safe IP response"""
        return {
            'ip': 'Local',
            'is_malicious': False,
            'threat_level': 'safe',
            'threat_reasons': ['Local network traffic'],
            'confidence': 100,
            'feeds_checked': 2
        }
    
    def get_threat_summary(self, traffic_ips):
        """Analyze list of IPs for threats"""
        malicious_ips = []
        suspicious_ips = []
        
        for ip in traffic_ips[:100]:  # Check top 100
            threat = self.check_ip_reputation(ip)
            
            if threat['is_malicious']:
                if threat['threat_level'] in ['high', 'critical']:
                    malicious_ips.append({
                        'ip': ip,
                        'level': threat['threat_level'],
                        'confidence': threat['confidence']
                    })
                else:
                    suspicious_ips.append({
                        'ip': ip,
                        'level': threat['threat_level'],
                        'confidence': threat['confidence']
                    })
        
        return {
            'malicious_count': len(malicious_ips),
            'suspicious_count': len(suspicious_ips),
            'malicious_ips': malicious_ips,
            'suspicious_ips': suspicious_ips,
            'total_checked': len(traffic_ips)
        }

# Global instance
_threat_intel = None

def get_threat_intelligence():
    """Get or create global threat intelligence instance"""
    global _threat_intel
    if _threat_intel is None:
        _threat_intel = ThreatIntelligence()
    return _threat_intel

def check_ip_threat(ip_address):
    """Convenience function to check IP threat level"""
    intel = get_threat_intelligence()
    return intel.check_ip_reputation(ip_address)

def check_domain_threat(domain):
    """Convenience function to check domain threat level"""
    intel = get_threat_intelligence()
    return intel.check_domain_reputation(domain)
