import os
import shlex
import subprocess

import docker

from games import create_game_plugin
from player_tracker import tracker as player_tracker


def resolve_docker_status(raw_status):
    if raw_status == "running":
        return "online"
    if raw_status in {"created", "restarting", "paused"}:
        return "busy"
    return "offline"


def run_shell_command(command, timeout_sec=15):
    try:
        result = subprocess.run(command, shell=True, capture_output=True, text=True, timeout=timeout_sec)
        return result.returncode, (result.stdout or ""), (result.stderr or "")
    except subprocess.TimeoutExpired:
        return 124, "", "command timed out"


def get_native_server_status(server_config):
    status_command = server_config["status_command"]
    process_name = server_config["process_name"]

    if status_command:
        code, _, _ = run_shell_command(status_command)
        return "online" if code == 0 else "offline"

    if process_name:
        code, _, _ = run_shell_command(f"pgrep -f {shlex.quote(process_name)}")
        return "online" if code == 0 else "offline"

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


def build_server_status(client, server_config):
    server_id = server_config["server_id"]
    game = server_config["game"]
    runtime = server_config["runtime"]
    container_name = server_config["container_name"]
    log_file_path = server_config["log_file_path"]
    address = server_config["address"]
    max_players = server_config["max_players"]
    plugin = create_game_plugin(game)

    if runtime == "native":
        status = get_native_server_status(server_config)
        day = 0
        players_list = []
        if status == "online":
            players_list = player_tracker.get_players(server_id)
            try:
                with open(log_file_path, "rb") as f:
                    f.seek(0, os.SEEK_END)
                    size = f.tell()
                    f.seek(max(size - 1024 * 1024, 0), os.SEEK_SET)
                    logs = f.read().decode("utf-8", errors="ignore")
                day = plugin.extract_day(logs)
            except Exception:
                day = 0
        else:
            player_tracker.clear_players(server_id)
            
        return {
            "name": server_id,
            "status": status,
            "address": address,
            "stats": {
                "players": f"{len(players_list)}/{max_players}",
                "player_names": players_list,
                "cpu": 0.0,
                "memory": 0.0,
            },
            "day": day,
        }

    try:
        container = client.containers.get(container_name)
        status = resolve_docker_status(container.status)

        cpu_pct, mem_gb = 0.0, 0.0
        day = 0
        players_list = []
        if status == "online":
            players_list = player_tracker.get_players(server_id)
            cpu_pct, mem_gb = read_container_metrics(container)
            try:
                logs = container.logs(tail=3000).decode("utf-8", errors="ignore")
                day = plugin.extract_day(logs)
            except Exception:
                day = 0
        else:
            player_tracker.clear_players(server_id)

        return {
            "name": server_id,
            "status": status,
            "address": address,
            "stats": {
                "players": f"{len(players_list)}/{max_players}",
                "player_names": players_list,
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


def start_server_instance(client, server_name, server_config):
    try:
        if server_config["runtime"] == "docker":
            container = client.containers.get(server_config["container_name"])
            container.reload()

            if container.status == "running":
                return {
                    "success": True,
                    "message": f"Server '{server_name}' is already running.",
                    "server_name": server_name,
                }, 200

            container.start()
            return {
                "success": True,
                "message": f"Server '{server_name}' is starting...",
                "server_name": server_name,
            }, 200

        start_command = server_config["start_command"]
        if not start_command:
            return {
                "success": False,
                "message": f"Server '{server_name}' has no start_command configured",
                "server_name": server_name,
            }, 400

        code, _, stderr = run_shell_command(start_command)
        if code != 0:
            return {
                "success": False,
                "message": stderr.strip() or "Failed to execute start_command",
                "server_name": server_name,
            }, 500

        return {
            "success": True,
            "message": f"Server '{server_name}' is starting...",
            "server_name": server_name,
        }, 200
    except docker.errors.NotFound:
        return {
            "success": False,
            "message": f"Container '{server_config['container_name']}' not found",
            "server_name": server_name,
        }, 404
    except Exception as e:
        return {
            "success": False,
            "message": str(e),
            "server_name": server_name,
        }, 500


def stop_server_instance(client, server_name, server_config):
    try:
        if server_config["runtime"] == "docker":
            container = client.containers.get(server_config["container_name"])
            container.reload()

            if container.status != "running":
                return {
                    "success": True,
                    "message": f"Server '{server_name}' is already stopped.",
                    "server_name": server_name,
                }, 200

            container.stop(timeout=30)
            return {
                "success": True,
                "message": f"Server '{server_name}' is stopping...",
                "server_name": server_name,
            }, 200

        stop_command = server_config["stop_command"]
        if not stop_command:
            return {
                "success": False,
                "message": f"Server '{server_name}' has no stop_command configured",
                "server_name": server_name,
            }, 400

        code, _, stderr = run_shell_command(stop_command)
        if code != 0:
            return {
                "success": False,
                "message": stderr.strip() or "Failed to execute stop_command",
                "server_name": server_name,
            }, 500

        return {
            "success": True,
            "message": f"Server '{server_name}' is stopping...",
            "server_name": server_name,
        }, 200
    except docker.errors.NotFound:
        return {
            "success": False,
            "message": f"Container '{server_config['container_name']}' not found",
            "server_name": server_name,
        }, 404
    except Exception as e:
        return {
            "success": False,
            "message": str(e),
            "server_name": server_name,
        }, 500
