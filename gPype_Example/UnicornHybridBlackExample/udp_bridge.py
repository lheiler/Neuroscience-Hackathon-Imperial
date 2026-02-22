# udp_bridge.py
# HTTP -> UDP bridge for browser stimulus triggers (START=1, END=2)

import socket
from flask import Flask, request, jsonify
from flask_cors import CORS

BRIDGE_HOST = "127.0.0.1"
BRIDGE_PORT = 8765

UDP_IP = "127.0.0.1"
UDP_PORT = 1000  # must match gp.UDPReceiver(port=1000)

app = Flask(__name__)
CORS(app)  # allow requests from localhost / file origins

sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)


def _send_udp_int(value: int):
  msg = str(int(value)).encode("ascii")  # gp.UDPReceiver expects ASCII digits
  sock.sendto(msg, (UDP_IP, UDP_PORT))


@app.get("/health")
def health():
  return jsonify({"ok": True, "udp_target": f"{UDP_IP}:{UDP_PORT}"})


@app.post("/trigger")
def trigger():
  data = request.get_json(force=True, silent=True) or {}

  # Expect { "value": 1 } or { "value": 2 }
  value = data.get("value", None)
  if value is None:
    return jsonify({"ok": False, "error": "Missing JSON field 'value' (expected 1 or 2)."}), 400

  try:
    value_int = int(value)
  except Exception:
    return jsonify({"ok": False, "error": "'value' must be an integer (1 or 2)."}), 400

  if value_int not in (0, 1, 2, 3, 4):
    return jsonify({"ok": False, "error": "'value' must be 0-4"}), 400

  try:
    _send_udp_int(value_int)
  except Exception as e:
    return jsonify({"ok": False, "error": f"UDP send failed: {e}"}), 500

  return jsonify({"ok": True, "sent": value_int})


if __name__ == "__main__":
  try:
    print(f"[udp_bridge] HTTP listening on http://{BRIDGE_HOST}:{BRIDGE_PORT}")
    print(f"[udp_bridge] Forwarding UDP to {UDP_IP}:{UDP_PORT}")
    app.run(host=BRIDGE_HOST, port=BRIDGE_PORT, debug=False, use_reloader=False, threaded=True)
  finally:
    try:
      sock.close()
    except Exception:
      pass