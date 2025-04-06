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
from packet_sniffer import start_sniffing

app = Flask(__name__)

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
    app.run(port=5000, debug=True)
