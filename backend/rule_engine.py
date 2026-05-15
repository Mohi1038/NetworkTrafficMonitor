"""
Custom Rule Engine - IDS-like detection rules
Similar to Suricata/Snort but simplified
"""

import json
import re
import os
from pathlib import Path
from datetime import datetime
from collections import defaultdict
import threading

RULES_DIR = Path(os.environ.get("NTM_RULES_DIR", Path(__file__).parent / ".ntm_rules"))
RULES_DIR.mkdir(exist_ok=True)
RULES_FILE = RULES_DIR / "custom_rules.json"
DEFAULT_RULES_FILE = Path(__file__).parent / "default_rules.json"

class RuleEngine:
    """Custom rule engine for network detection"""
    
    def __init__(self):
        self.rules = self._load_rules()
        self.lock = threading.Lock()
        self.rule_hits = defaultdict(int)
        self.alerts = []
    
    def _load_rules(self):
        """Load custom rules from JSON file"""
        rules = []
        
        # Load custom rules if they exist
        if RULES_FILE.exists():
            try:
                with open(RULES_FILE, 'r') as f:
                    rules = json.load(f)
                print(f"[RuleEngine] Loaded {len(rules)} custom rules")
            except Exception as e:
                print(f"[RuleEngine] Error loading rules: {e}")
        
        # Add default rules
        default_rules = self._get_default_rules()
        rules.extend(default_rules)
        
        return rules
    
    def _get_default_rules(self):
        """Get built-in default detection rules"""
        return [
            {
                'id': 'rule_001',
                'name': 'Suspicious SSH Brute Force',
                'enabled': True,
                'conditions': {
                    'protocol': 'TCP',
                    'dst_port': 22,
                    'packet_rate_threshold': 50
                },
                'action': 'alert',
                'severity': 'high'
            },
            {
                'id': 'rule_002',
                'name': 'Port Scanning Detection',
                'enabled': True,
                'conditions': {
                    'connection_rate_threshold': 30,
                    'unique_dst_ports': 10
                },
                'action': 'alert',
                'severity': 'high'
            },
            {
                'id': 'rule_003',
                'name': 'Suspicious DNS Queries',
                'enabled': True,
                'conditions': {
                    'protocol': 'UDP',
                    'dst_port': 53,
                    'query_rate_threshold': 100
                },
                'action': 'alert',
                'severity': 'medium'
            },
            {
                'id': 'rule_004',
                'name': 'FTP Suspicious Activity',
                'enabled': True,
                'conditions': {
                    'protocol': 'TCP',
                    'dst_port': 21,
                    'byte_rate_threshold': 1000000
                },
                'action': 'alert',
                'severity': 'medium'
            },
            {
                'id': 'rule_005',
                'name': 'Telnet Attempt (Insecure)',
                'enabled': True,
                'conditions': {
                    'protocol': 'TCP',
                    'dst_port': 23
                },
                'action': 'warn',
                'severity': 'low'
            },
            {
                'id': 'rule_006',
                'name': 'ICMP Flood Detection',
                'enabled': True,
                'conditions': {
                    'protocol': 'ICMP',
                    'packet_rate_threshold': 1000
                },
                'action': 'alert',
                'severity': 'high'
            },
            {
                'id': 'rule_007',
                'name': 'SQL Injection Attempt Signature',
                'enabled': True,
                'conditions': {
                    'dst_port': [80, 443, 8080],
                    'payload_regex': r'(union|select|insert|delete|drop|update).*from'
                },
                'action': 'alert',
                'severity': 'critical'
            },
            {
                'id': 'rule_008',
                'name': 'Unusual HTTP Methods',
                'enabled': True,
                'conditions': {
                    'protocol': 'TCP',
                    'dst_port': [80, 443],
                    'http_method_regex': r'^(TRACE|CONNECT|PROPFIND)'
                },
                'action': 'warn',
                'severity': 'medium'
            }
        ]
    
    def add_rule(self, rule):
        """Add a new custom rule"""
        required_fields = ['id', 'name', 'enabled', 'conditions', 'action', 'severity']
        
        for field in required_fields:
            if field not in rule:
                return False, f"Missing required field: {field}"
        
        with self.lock:
            # Check if rule ID already exists
            if any(r['id'] == rule['id'] for r in self.rules):
                return False, f"Rule ID already exists: {rule['id']}"
            
            self.rules.append(rule)
            self._save_rules()
            return True, f"Rule added successfully: {rule['id']}"
    
    def update_rule(self, rule_id, updated_rule):
        """Update an existing rule"""
        with self.lock:
            for i, rule in enumerate(self.rules):
                if rule['id'] == rule_id:
                    self.rules[i] = updated_rule
                    self._save_rules()
                    return True, f"Rule updated: {rule_id}"
            return False, f"Rule not found: {rule_id}"
    
    def delete_rule(self, rule_id):
        """Delete a rule"""
        with self.lock:
            self.rules = [r for r in self.rules if r['id'] != rule_id]
            self._save_rules()
            return True, f"Rule deleted: {rule_id}"
    
    def _save_rules(self):
        """Save rules to disk"""
        try:
            custom_rules = [r for r in self.rules if r['id'].startswith('custom_')]
            with open(RULES_FILE, 'w') as f:
                json.dump(custom_rules, f, indent=2)
        except Exception as e:
            print(f"[RuleEngine] Error saving rules: {e}")
    
    def evaluate_packet(self, packet_data):
        """Evaluate packet against all enabled rules"""
        alerts = []
        
        with self.lock:
            for rule in self.rules:
                if not rule['enabled']:
                    continue
                
                if self._match_conditions(packet_data, rule['conditions']):
                    self.rule_hits[rule['id']] += 1
                    
                    alert = {
                        'rule_id': rule['id'],
                        'rule_name': rule['name'],
                        'action': rule['action'],
                        'severity': rule['severity'],
                        'timestamp': datetime.now().isoformat(),
                        'packet_data': packet_data
                    }
                    
                    alerts.append(alert)
                    self.alerts.append(alert)
        
        # Keep only last 1000 alerts
        if len(self.alerts) > 1000:
            self.alerts = self.alerts[-1000:]
        
        return alerts
    
    def _match_conditions(self, packet_data, conditions):
        """Check if packet matches rule conditions"""
        
        # Protocol match
        if 'protocol' in conditions:
            if packet_data.get('protocol') != conditions['protocol']:
                return False
        
        # Port match
        if 'dst_port' in conditions:
            ports = conditions['dst_port']
            if isinstance(ports, int):
                ports = [ports]
            if packet_data.get('dst_port') not in ports:
                return False
        
        # Packet rate threshold
        if 'packet_rate_threshold' in conditions:
            if packet_data.get('packet_rate', 0) < conditions['packet_rate_threshold']:
                return False
        
        # Connection rate threshold
        if 'connection_rate_threshold' in conditions:
            if packet_data.get('connection_rate', 0) < conditions['connection_rate_threshold']:
                return False
        
        # Byte rate threshold
        if 'byte_rate_threshold' in conditions:
            if packet_data.get('byte_rate', 0) < conditions['byte_rate_threshold']:
                return False
        
        # Regex patterns
        if 'payload_regex' in conditions:
            payload = packet_data.get('payload', '')
            pattern = conditions['payload_regex']
            if not re.search(pattern, payload, re.IGNORECASE):
                return False
        
        if 'http_method_regex' in conditions:
            method = packet_data.get('http_method', '')
            pattern = conditions['http_method_regex']
            if not re.search(pattern, method, re.IGNORECASE):
                return False
        
        return True
    
    def get_rules(self, enabled_only=False):
        """Get all rules"""
        if enabled_only:
            return [r for r in self.rules if r['enabled']]
        return self.rules
    
    def get_alerts(self, limit=100):
        """Get recent rule alerts"""
        return self.alerts[-limit:]
    
    def get_rule_statistics(self):
        """Get rule evaluation statistics"""
        with self.lock:
            stats = {
                'total_rules': len(self.rules),
                'enabled_rules': len([r for r in self.rules if r['enabled']]),
                'total_hits': sum(self.rule_hits.values()),
                'top_triggered_rules': sorted(
                    [(rule_id, count) for rule_id, count in self.rule_hits.items()],
                    key=lambda x: x[1],
                    reverse=True
                )[:10]
            }
        return stats

# Global instance
_rule_engine = None

def get_rule_engine():
    """Get or create global rule engine"""
    global _rule_engine
    if _rule_engine is None:
        _rule_engine = RuleEngine()
    return _rule_engine

def evaluate_packet(packet_data):
    """Convenience function to evaluate packet against rules"""
    engine = get_rule_engine()
    return engine.evaluate_packet(packet_data)
