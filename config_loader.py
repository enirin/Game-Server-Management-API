import os

import yaml


def normalize_server_aliases(raw_aliases, index):
    if raw_aliases is None:
        return []

    if not isinstance(raw_aliases, list):
        raise ValueError(f"servers[{index}].server_aliases must be a list")

    normalized_aliases = []
    seen_aliases = set()
    for alias_index, alias in enumerate(raw_aliases):
        alias_text = str(alias).strip()
        if not alias_text:
            raise ValueError(f"servers[{index}].server_aliases[{alias_index}] must not be empty")
        if alias_text in seen_aliases:
            continue
        seen_aliases.add(alias_text)
        normalized_aliases.append(alias_text)

    return normalized_aliases


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
    claimed_names = {}
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
        server_aliases = normalize_server_aliases(server.get("server_aliases"), index)
        server_id = str(server["server_id"])

        if runtime == "docker" and not container_name:
            raise ValueError(f"servers[{index}] requires container_name when runtime=docker")
        if runtime == "native" and not log_file_path:
            raise ValueError(f"servers[{index}] requires log_file_path when runtime=native")

        claimed_names[server_id] = claimed_names.get(server_id, []) + [f"servers[{index}].server_id"]
        for alias_index, alias in enumerate(server_aliases):
            claimed_names[alias] = claimed_names.get(alias, []) + [f"servers[{index}].server_aliases[{alias_index}]"]

        normalized_servers.append(
            {
                "server_id": server_id,
                "game": str(server["game"]),
                "runtime": runtime,
                "container_name": str(container_name or ""),
                "address": str(server["address"]),
                "max_players": int(server["max_players"]),
                "server_aliases": server_aliases,
                "channel_id": channel_id,
                "log_file_path": str(log_file_path or ""),
                "process_name": str(process_name or ""),
                "status_command": str(status_command or ""),
                "start_command": str(start_command or ""),
                "stop_command": str(stop_command or ""),
            }
        )

    duplicate_names = {name: refs for name, refs in claimed_names.items() if len(refs) > 1}
    if duplicate_names:
        collisions = "; ".join(f"{name}: {', '.join(refs)}" for name, refs in sorted(duplicate_names.items()))
        raise ValueError(f"server_id and server_aliases must be unique across all servers: {collisions}")

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
