import os

from flask import Flask, jsonify
from flask_cors import CORS

from config_loader import load_config
from discord_notifier import DiscordNotifier
from log_watcher import start_log_watchers
from server_runtime import build_server_status, start_server_instance, stop_server_instance

app = Flask(__name__)
CORS(app)

CONFIG_PATH = os.path.join(os.path.dirname(__file__), "config.yaml")


CONFIG = load_config(CONFIG_PATH)
SERVERS = CONFIG["servers"]
SERVERS_BY_ID = {server["server_id"]: server for server in SERVERS}
notifier = DiscordNotifier(
    tell_url=CONFIG["discord"]["tell_url"],
    web_endpoint_token=CONFIG["discord"]["web_endpoint_token"],
    timeout_sec=CONFIG["discord"]["request_timeout_sec"],
)


def find_server_or_404(server_name):
    server = SERVERS_BY_ID.get(server_name)
    if not server:
        return None, (jsonify({"success": False, "message": f"Server '{server_name}' not found"}), 404)
    return server, None


@app.route("/list", methods=["GET"])
def list_servers():
    try:
        payload = [build_server_status(server) for server in SERVERS]
        return jsonify({"servers": payload})
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500


@app.route("/start/<server_name>", methods=["POST"])
def start_server(server_name):
    server, error_response = find_server_or_404(server_name)
    if error_response:
        return error_response

    payload, status_code = start_server_instance(server_name, server)
    return jsonify(payload), status_code


@app.route("/stop/<server_name>", methods=["POST"])
def stop_server(server_name):
    server, error_response = find_server_or_404(server_name)
    if error_response:
        return error_response

    payload, status_code = stop_server_instance(server_name, server)
    return jsonify(payload), status_code


if __name__ == "__main__":
    start_log_watchers(notifier, SERVERS)
    app.run(host="0.0.0.0", port=CONFIG["api"]["port"])
