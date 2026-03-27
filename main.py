import os

from flask import Flask, jsonify
from flask_cors import CORS

from config_loader import load_config
from discord_notifier import DiscordNotifier
from log_watcher import start_log_watchers
from management_service import ManagementError, ManagementService

app = Flask(__name__)
CORS(app)

CONFIG_PATH = os.path.join(os.path.dirname(__file__), "config.yaml")


CONFIG = load_config(CONFIG_PATH)
SERVERS = CONFIG["servers"]
management_service = ManagementService(SERVERS, base_dir=os.path.dirname(__file__))
notifier = DiscordNotifier(
    tell_url=CONFIG["discord"]["tell_url"],
    web_endpoint_token=CONFIG["discord"]["web_endpoint_token"],
    timeout_sec=CONFIG["discord"]["request_timeout_sec"],
)


def handle_management_error(error: ManagementError):
    return jsonify({"success": False, "message": error.message}), int(error.status_code)


@app.route("/list", methods=["GET"])
def list_servers():
    try:
        return jsonify(management_service.list_servers())
    except ManagementError as error:
        return handle_management_error(error)
    except Exception as error:
        return jsonify({"success": False, "message": str(error)}), 500


@app.route("/start/<server_name>", methods=["POST"])
def start_server(server_name):
    try:
        return jsonify(management_service.start_server(server_name)), 200
    except ManagementError as error:
        return handle_management_error(error)
    except Exception as error:
        return jsonify({"success": False, "message": str(error)}), 500


@app.route("/stop/<server_name>", methods=["POST"])
def stop_server(server_name):
    try:
        return jsonify(management_service.stop_server(server_name)), 200
    except ManagementError as error:
        return handle_management_error(error)
    except Exception as error:
        return jsonify({"success": False, "message": str(error)}), 500


if __name__ == "__main__":
    start_log_watchers(notifier, SERVERS)
    app.run(host="0.0.0.0", port=CONFIG["api"]["port"])
