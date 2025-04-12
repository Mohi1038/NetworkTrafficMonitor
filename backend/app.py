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
from flask import Flask, jsonify
import threading
import os
from ml_model.packet_sniffer_2 import start_sniffing
from utils import stats
from pathlib import Path
import json
from collections import defaultdict

app = Flask(__name__)

DATA_FILE = "network_data.json"
# Ensure file exists once

def temp():
    if not Path(DATA_FILE).exists():
    
        with open(DATA_FILE, "w") as f:
            json.dump({}, f)

        stats.update({
        "total_incoming_bytes": 0,
        "total_outgoing_bytes": 0,
        "speed": {"incoming_kbps": 0, "outgoing_kbps": 0},
        "protocol_distribution": defaultdict(int),
        # "top_ips": defaultdict(int),
        # "top_ips": defaultdict(lambda: {"hostname": "", "app": "", "total_bytes": 0}),
        "top_ips": defaultdict(lambda: {"hostname": "", "app": "", "incoming_bytes": 0, "outgoing_bytes": 0}),
        
        "traffic_table": []
        })
    else:
        with open("network_data.json", 'r') as file:
            data = defaultdict(int)
            data = json.load(file)
            stats["speed"] = data["speed"]
            stats['total_incoming_bytes'] = data['total_incoming_bytes']
            stats['protocol_distribution'] = data['protocol_distribution']
            stats['total_outgoing_bytes'] = data['total_outgoing_bytes']
            stats['top_ips'] = data['top_ips']
            stats['traffic_table'] = data['traffic_table']
    return


@app.route("/api/data")
def get_data():
    if not os.path.exists("network_data.json"):
        return jsonify({"error": "Data file not found"}), 404

    with open("network_data.json") as f:
        data = f.read()
    return app.response_class(data, content_type="application/json")

# Start sniffing in background
threading.Thread(target=start_sniffing, daemon=True).start()

if __name__ == "__main__":
    temp()
    app.run(port=5000, debug=True)