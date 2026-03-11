import os
import re
import threading
import time

import docker
import requests
import yaml
from flask import Flask, jsonify
from flask_cors import CORS

from discord_notifier import DiscordNotifier
from log_parsers import get_parser

app = Flask(__name__)
CORS(app)

client = docker.from_env()
CONFIG_PATH = os.path.join(os.path.dirname(__file__), "config.yaml")


def load_config(config_path):
    if not os.path.exists(config_path):
        raise FileNotFoundError(f"config.yaml not found: {config_path}")

    with open(config_path, "r", encoding="utf-8") as f:
        config = yaml.safe_load(f) or {}

    if "servers" not in config or not isinstance(config["servers"], list) or not config["servers"]:
        raise ValueError("config.yaml must contain a non-empty 'servers' list")

    discord_cfg = config.get("discord", {})
    tell_url = str(discord_cfg.get("tell_url", "http://127.0.0.1:5050/tell"))
    web_endpoint_token = str(discord_cfg.get("web_endpoint_token", ""))
    timeout_sec = int(discord_cfg.get("request_timeout_sec", 5))

    normalized_servers = []
    for index, server in enumerate(config["servers"]):
        if not isinstance(server, dict):
            raise ValueError(f"servers[{index}] must be an object")

        required_keys = ["server_id", "container_name", "address", "max_players", "game"]
        missing_keys = [key for key in required_keys if key not in server]
        if missing_keys:
            raise ValueError(f"servers[{index}] is missing keys: {', '.join(missing_keys)}")

        channel_id = server.get("channel_id")
        if channel_id is not None:
            channel_id = int(channel_id)

        normalized_servers.append(
            {
                "server_id": str(server["server_id"]),
                "game": str(server["game"]),
                "container_name": str(server["container_name"]),
                "address": str(server["address"]),
                "max_players": int(server["max_players"]),
                "channel_id": channel_id,
            }
        )

    return {
        "servers": normalized_servers,
        "discord": {
            "tell_url": tell_url,
            "web_endpoint_token": web_endpoint_token,
            "request_timeout_sec": timeout_sec,
        },
    }


CONFIG = load_config(CONFIG_PATH)
SERVERS = CONFIG["servers"]
SERVERS_BY_ID = {server["server_id"]: server for server in SERVERS}
NOTIFIER = DiscordNotifier(
    tell_url=CONFIG["discord"]["tell_url"],
    web_endpoint_token=CONFIG["discord"]["web_endpoint_token"],
    timeout_sec=CONFIG["discord"]["request_timeout_sec"],
)


def watch_server_logs(server_config):
    server_id = server_config["server_id"]
    game = server_config["game"]
    container_name = server_config["container_name"]
    channel_id = server_config.get("channel_id")
    parser = get_parser(game)
    log_prefix = f"[{server_id}/{container_name}]"

    while True:
        try:
            container = client.containers.get(container_name)
            container.reload()

            if container.status != "running":
                time.sleep(2)
                continue

            for raw_line in container.logs(stream=True, follow=True, tail=0):
                message = raw_line.decode("utf-8", errors="ignore").rstrip()
                if message:
                    print(f"{log_prefix} {message}")
                    event = parser.parse(message)
                    if event:
                        try:
                            NOTIFIER.send_presence_event(
                                server_id=server_id,
                                game=game,
                                event=event,
                                channel_id=channel_id,
                            )
                            print(f"{log_prefix} sent presence event: {event.event_type} {event.player_name}")
                        except requests.RequestException as e:
                            print(f"{log_prefix} failed to send tell request: {e}")
        except docker.errors.NotFound:
            print(f"{log_prefix} container not found")
            time.sleep(3)
        except Exception as e:
            print(f"{log_prefix} log watcher error: {e}")
            time.sleep(3)


def start_log_watchers():
    for server in SERVERS:
        thread = threading.Thread(target=watch_server_logs, args=(server,), daemon=True)
        thread.start()


def resolve_status(raw_status):
    if raw_status == "running":
        return "online"
    if raw_status in {"created", "restarting", "paused"}:
        return "busy"
    return "offline"


def read_container_metrics(container):
    cpu_pct = 0.0
    mem_gb = 0.0

    try:
        stats = container.stats(stream=False)
        mem_usage = stats.get("memory_stats", {}).get("usage", 0)
        mem_gb = round(mem_usage / (1024 ** 3), 2)

        cpu_total = stats.get("cpu_stats", {}).get("cpu_usage", {}).get("total_usage", 0)
        prev_cpu_total = stats.get("precpu_stats", {}).get("cpu_usage", {}).get("total_usage", 0)
        system_total = stats.get("cpu_stats", {}).get("system_cpu_usage", 0)
        prev_system_total = stats.get("precpu_stats", {}).get("system_cpu_usage", 0)

        cpu_delta = cpu_total - prev_cpu_total
        system_delta = system_total - prev_system_total
        if system_delta > 0:
            online_cpus = stats.get("cpu_stats", {}).get("online_cpus", 1)
            cpu_pct = round((cpu_delta / system_delta) * online_cpus * 100.0, 1)
    except Exception:
        pass

    return cpu_pct, mem_gb


def read_server_day(container):
    try:
        logs = container.logs(tail=3000).decode("utf-8", errors="ignore")
        day_match = re.findall(r"Day[:\\s]+(\\d+)", logs, re.IGNORECASE)
        return int(day_match[-1]) if day_match else 0
    except Exception:
        return 0


def build_server_status(server_config):
    server_id = server_config["server_id"]
    container_name = server_config["container_name"]
    address = server_config["address"]
    max_players = server_config["max_players"]

    try:
        container = client.containers.get(container_name)
        status = resolve_status(container.status)

        cpu_pct, mem_gb = 0.0, 0.0
        day = 0
        if status == "online":
            cpu_pct, mem_gb = read_container_metrics(container)
            day = read_server_day(container)

        return {
            "name": server_id,
            "status": status,
            "address": address,
            "stats": {
                "players": f"0/{max_players}",
                "cpu": cpu_pct,
                "memory": mem_gb,
            },
            "day": day,
        }
    except docker.errors.NotFound:
        return {
            "name": server_id,
            "status": "offline",
            "address": address,
            "stats": {
                "players": f"0/{max_players}",
                "cpu": 0.0,
                "memory": 0.0,
            },
            "day": 0,
        }


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

    try:
        container = client.containers.get(server["container_name"])
        container.reload()

        if container.status == "running":
            return jsonify(
                {
                    "success": True,
                    "message": f"Server '{server_name}' is already running.",
                    "server_name": server_name,
                }
            )

        container.start()
        return jsonify(
            {
                "success": True,
                "message": f"Server '{server_name}' is starting...",
                "server_name": server_name,
            }
        )
    except docker.errors.NotFound:
        return jsonify({"success": False, "message": f"Container '{server['container_name']}' not found"}), 404
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500


@app.route("/stop/<server_name>", methods=["POST"])
def stop_server(server_name):
    server, error_response = find_server_or_404(server_name)
    if error_response:
        return error_response

    try:
        container = client.containers.get(server["container_name"])
        container.reload()

        if container.status != "running":
            return jsonify(
                {
                    "success": True,
                    "message": f"Server '{server_name}' is already stopped.",
                    "server_name": server_name,
                }
            )

        container.stop(timeout=30)
        return jsonify(
            {
                "success": True,
                "message": f"Server '{server_name}' is stopping...",
                "server_name": server_name,
            }
        )
    except docker.errors.NotFound:
        return jsonify({"success": False, "message": f"Container '{server['container_name']}' not found"}), 404
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500


if __name__ == "__main__":
    start_log_watchers()
    app.run(host="0.0.0.0", port=5000)
