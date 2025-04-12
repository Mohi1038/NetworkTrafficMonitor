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
from flask import Flask, jsonify
import threading
from pack_sniffer import start_sniffing, set_alert_callback
from utils import stats
from pathlib import Path
import json
from collections import defaultdict
from alert_mail import alert_callback

app = Flask(__name__)

DATA_FILE = "network_data.json"

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

# ---------- Send Email When Flask Starts ----------
def trigger_test_email():
    time.sleep(2)
    print("[INFO] Sending test email from app startup...")
    alert_callback("DDoS-Test", "127.0.0.1", "127.0.0.1", "TCP")

# ---------- API Endpoint ----------
@app.route("/api/data")
def get_data():
    if not Path(DATA_FILE).exists():
        return jsonify({"error": "Data file not found"}), 404

    with open(DATA_FILE) as f:
        data = f.read()
    return app.response_class(data, content_type="application/json")

if __name__ == "__main__":
    temp()

    # Start the email trigger in a separate thread after a small delay
    threading.Thread(target=trigger_test_email, daemon=True).start()

    app.run(port=5000, debug=True)
