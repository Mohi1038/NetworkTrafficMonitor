# from flask import Flask, jsonify
# from threading import Thread
# from packet_sniffer import start_sniffing
# from traffic_analyzer import get_traffic_summary
# from network_speed_monitor import get_current_speed

# app = Flask(__name__)

# @app.route('/api/traffic')
# def traffic_data():
#     summary = get_traffic_summary()
#     return jsonify(summary)


# if __name__ == '__main__':
#     sniffer_thread = Thread(target=start_sniffing, daemon=True)
#     sniffer_thread.start()
#     app.run(port=5000)


'''After JSON'''
import time
import os
from pathlib import Path

try:
    from dotenv import load_dotenv
except ImportError:
    load_dotenv = None

# Load environment variables from .env file
if load_dotenv:
    load_dotenv(dotenv_path=Path(__file__).parent.parent / '.env')

from flask import Flask, jsonify
import subprocess
import shutil
from flask_cors import CORS
import threading
from flask import request
from pack_sniffer import start_sniffing, set_alert_callback
from utils import stats
import json
from collections import defaultdict
from alert_mail import alert_callback

app = Flask(__name__)
CORS(app, resources={r"/api/*": {"origins": "*"}}, allow_headers=["Content-Type"], methods=["GET", "POST", "OPTIONS"])
from geoip_mapper import get_geoip_mapper, get_map_data
from ddos_detector import get_ddos_detector
from threat_intelligence import get_threat_intelligence, check_ip_threat
from rule_engine import get_rule_engine

BASE_DIR = Path(__file__).parent
DATA_FILE = BASE_DIR / "network_data.json"

# ---------- JSON File Init ----------
def temp():
    if not Path(DATA_FILE).exists():
        with open(DATA_FILE, "w") as f:
            json.dump({}, f)

        stats.update({
            "total_incoming_bytes": 0,
            "total_outgoing_bytes": 0,
            "speed": {"incoming_kbps": 0, "outgoing_kbps": 0},
            "protocol_distribution": defaultdict(int),
            "top_ips": defaultdict(lambda: {"hostname": "", "app": "", "incoming_bytes": 0, "outgoing_bytes": 0}),
            "traffic_table": []
        })
    else:
        with open(DATA_FILE, 'r') as file:
            data = json.load(file)
            stats["speed"] = data.get("speed", {})
            stats["total_incoming_bytes"] = data.get("total_incoming_bytes", 0)
            stats["total_outgoing_bytes"] = data.get("total_outgoing_bytes", 0)
            stats["protocol_distribution"] = data.get("protocol_distribution", {})
            stats["top_ips"] = data.get("top_ips", {})
            stats["traffic_table"] = data.get("traffic_table", [])

set_alert_callback(alert_callback)

threading.Thread(target=start_sniffing, daemon=True).start()

# ---------- Health Check Endpoint ----------
@app.route("/api/health")
def health_check():
    return jsonify({"status": "ok", "message": "Backend is running"}), 200

# ---------- API Endpoint ----------
@app.route("/api/data")
def get_data():
    if not Path(DATA_FILE).exists():
        return jsonify({"error": "Data file not found"}), 404

    with open(DATA_FILE) as f:
        data = f.read()
    return app.response_class(data, content_type="application/json")

# ---------- GeoIP Mapping Endpoints ----------
@app.route("/api/geomap")
def geomap():
    try:
        geoip = get_geoip_mapper()
        with open(DATA_FILE) as f:
            data = json.load(f)
        traffic_table = data.get("traffic_table", [])
        map_data = geoip.get_traffic_map_data(traffic_table)
        return jsonify({"success": True, "data": map_data}), 200
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

# ---------- DDoS Detection Endpoints ----------
@app.route("/api/ddos/alerts")
def ddos_alerts():
    try:
        ddos = get_ddos_detector()
        alerts = ddos.get_alerts(limit=50)
        stats_data = ddos.get_statistics()
        return jsonify({"success": True, "alerts": alerts, "statistics": stats_data}), 200
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

# ---------- Threat Intelligence Endpoints ----------
@app.route("/api/threat/check/<ip_address>")
def threat_check(ip_address):
    try:
        threat_intel = get_threat_intelligence()
        threat_data = threat_intel.check_ip_reputation(ip_address)
        return jsonify(threat_data), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/api/threat/summary")
def threat_summary():
    try:
        threat_intel = get_threat_intelligence()
        with open(DATA_FILE) as f:
            data = json.load(f)
        traffic_ips = list(set(entry.get('src_ip', '') for entry in data.get("traffic_table", [])))
        summary = threat_intel.get_threat_summary(traffic_ips)
        return jsonify({"success": True, "summary": summary}), 200
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

# ---------- Custom Rule Engine Endpoints ----------
@app.route("/api/rules")
def get_rules():
    try:
        rule_engine = get_rule_engine()
        rules = rule_engine.get_rules()
        return jsonify({"success": True, "rules": rules, "total": len(rules)}), 200
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@app.route("/api/rules/add", methods=["POST"])
def add_rule():
    try:
        rule_engine = get_rule_engine()
        rule_data = request.get_json()
        success, message = rule_engine.add_rule(rule_data)
        return jsonify({"success": success, "message": message}), 200 if success else 400
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@app.route("/api/rules/alerts")
def rule_alerts():
    try:
        rule_engine = get_rule_engine()
        alerts = rule_engine.get_alerts(limit=100)
        stats_data = rule_engine.get_rule_statistics()
        return jsonify({"success": True, "alerts": alerts, "statistics": stats_data}), 200
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


# ---------- Settings: notification email ----------
@app.route('/api/settings/notify_email', methods=['POST'])
def set_notify_email():
    try:
        payload = request.get_json(silent=True) or {}
        receiver = payload.get('receiver')
        sender = payload.get('sender')
        if not receiver:
            return jsonify({'success': False, 'error': 'receiver is required'}), 400

        cfg = {}
        cfg_path = BASE_DIR / 'email_settings.json'
        if cfg_path.exists():
            try:
                cfg = json.loads(cfg_path.read_text())
            except Exception:
                cfg = {}

        cfg['receiver'] = receiver
        if sender:
            cfg['sender'] = sender
        cfg_path.write_text(json.dumps(cfg))
        return jsonify({'success': True, 'message': 'Notification email saved'}), 200
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/settings/test_email', methods=['POST'])
def test_notify_email():
    try:
        payload = request.get_json(silent=True) or {}
        subject = payload.get('subject', 'Network Monitor - Test Email')
        body = payload.get('body', 'This is a test email from Network Traffic Monitor.')
        # Attempt to send a test email using alert_mail
        from alert_mail import send_email_alert
        send_email_alert(subject, body)
        return jsonify({'success': True, 'message': 'Test email attempted (check server logs).'}), 200
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/settings/email_config', methods=['GET','POST'])
def email_config():
    """
    Email config endpoint: only stores receiver email address.
    SMTP credentials must be set via environment variables:
      - ALERT_EMAIL_SENDER
      - ALERT_EMAIL_RECEIVER (overrides UI receiver if set)
      - ALERT_EMAIL_PASSWORD
      - ALERT_SMTP_HOST
      - ALERT_SMTP_PORT
      - ALERT_SMTP_USER
      - ALERT_SMTP_SSL
    """
    try:
        cfg_path = BASE_DIR / 'email_settings.json'
        if request.method == 'GET':
            if cfg_path.exists():
                cfg = json.loads(cfg_path.read_text())
                # Only return receiver email (not SMTP creds)
                return jsonify({'success': True, 'config': {'receiver': cfg.get('receiver', '')}}), 200
            return jsonify({'success': True, 'config': {}}), 200

        # POST: save only receiver email, ignore SMTP fields
        payload = request.get_json(silent=True) or {}
        receiver = payload.get('receiver', '').strip()
        if not receiver:
            return jsonify({'success': False, 'error': 'receiver email required'}), 400
        
        # Load existing config (preserves any legacy SMTP settings if present)
        cfg = {}
        if cfg_path.exists():
            try:
                cfg = json.loads(cfg_path.read_text())
            except Exception:
                pass
        
        # Update receiver only
        cfg['receiver'] = receiver
        cfg_path.write_text(json.dumps(cfg))
        return jsonify({'success': True, 'message': 'Email configuration saved'}), 200
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

# ---------- Bandwidth Capacity Test Endpoints ----------
@app.route("/api/speedtest/start", methods=["POST"])
def start_speedtest():
    """Start a capacity test (measures actual peak bandwidth)"""
    try:
        from bandwidth_tester import get_bandwidth_tester
        tester = get_bandwidth_tester()
        payload = request.get_json(silent=True) or {}
        duration = int(payload.get("duration", 15))
        workers = int(payload.get("workers", 8))
        repeats = int(payload.get("repeats", 3))
        result = tester.run_async_test(duration=duration, workers=workers, repeats=repeats)
        return jsonify(result), 200
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@app.route("/api/speedtest/status")
def speedtest_status():
    """Get current speedtest status and results"""
    try:
        from bandwidth_tester import get_bandwidth_tester
        tester = get_bandwidth_tester()
        results = tester.get_test_results()
        return jsonify({"success": True, "data": results}), 200
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@app.route("/api/speedtest/results")
def speedtest_results():
    """Get latest speedtest results"""
    try:
        from bandwidth_tester import get_bandwidth_tester
        tester = get_bandwidth_tester()
        results = tester.get_test_results()
        return jsonify({
            "success": True,
            "download_mbps": results["download_mbps"],
            "upload_mbps": results["upload_mbps"],
            "test_status": results["test_status"],
            "timestamp": results["timestamp"]
        }), 200
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500



if __name__ == "__main__":
    temp()
    port = int(os.environ.get('FLASK_PORT', 5001))
    host = os.environ.get('FLASK_HOST', '127.0.0.1')
    debug = os.environ.get('FLASK_DEBUG', 'False').lower() == 'true'
    print(f"[INFO] Starting Flask server on {host}:{port}...")
    app.run(host=host, port=port, debug=debug, use_reloader=False)
