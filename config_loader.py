import os

import yaml


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

    api_cfg = config.get("api", {})
    port = int(api_cfg.get("port", 5000))

    normalized_servers = []
    for index, server in enumerate(config["servers"]):
        if not isinstance(server, dict):
            raise ValueError(f"servers[{index}] must be an object")

        required_keys = ["server_id", "address", "max_players", "game"]
        missing_keys = [key for key in required_keys if key not in server]
        if missing_keys:
            raise ValueError(f"servers[{index}] is missing keys: {', '.join(missing_keys)}")

        runtime = str(server.get("runtime", "docker")).strip().lower()
        if runtime not in {"docker", "native"}:
            raise ValueError(f"servers[{index}].runtime must be 'docker' or 'native'")

        channel_id = server.get("channel_id")
        if channel_id is not None:
            channel_id = int(channel_id)

        container_name = server.get("container_name")
        log_file_path = server.get("log_file_path")
        process_name = server.get("process_name")
        status_command = server.get("status_command")
        start_command = server.get("start_command")
        stop_command = server.get("stop_command")

        if runtime == "docker" and not container_name:
            raise ValueError(f"servers[{index}] requires container_name when runtime=docker")
        if runtime == "native" and not log_file_path:
            raise ValueError(f"servers[{index}] requires log_file_path when runtime=native")

        normalized_servers.append(
            {
                "server_id": str(server["server_id"]),
                "game": str(server["game"]),
                "runtime": runtime,
                "container_name": str(container_name or ""),
                "address": str(server["address"]),
                "max_players": int(server["max_players"]),
                "channel_id": channel_id,
                "log_file_path": str(log_file_path or ""),
                "process_name": str(process_name or ""),
                "status_command": str(status_command or ""),
                "start_command": str(start_command or ""),
                "stop_command": str(stop_command or ""),
            }
        )

    return {
        "servers": normalized_servers,
        "discord": {
            "tell_url": tell_url,
            "web_endpoint_token": web_endpoint_token,
            "request_timeout_sec": timeout_sec,
        },
        "api": {
            "port": port,
        },
    }
