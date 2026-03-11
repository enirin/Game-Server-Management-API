import os
import threading
import time

import docker
import requests

from log_parsers import get_parser


def stream_docker_log_lines(client, container_name):
    container = client.containers.get(container_name)
    container.reload()

    if container.status != "running":
        time.sleep(2)
        return

    for raw_line in container.logs(stream=True, follow=True, tail=0):
        yield raw_line.decode("utf-8", errors="ignore").rstrip()


def stream_native_log_lines(log_file_path):
    if not os.path.isfile(log_file_path):
        raise FileNotFoundError(log_file_path)

    with open(log_file_path, "r", encoding="utf-8", errors="ignore") as f:
        # 既存ログは読み飛ばして新着のみ追従する
        f.seek(0, os.SEEK_END)
        while True:
            line = f.readline()
            if not line:
                time.sleep(0.3)
                continue
            yield line.rstrip("\r\n")


def watch_server_logs(client, notifier, server_config):
    server_id = server_config["server_id"]
    game = server_config["game"]
    runtime = server_config["runtime"]
    container_name = server_config["container_name"]
    log_file_path = server_config["log_file_path"]
    channel_id = server_config.get("channel_id")
    parser = get_parser(game)
    source_name = container_name if runtime == "docker" else (log_file_path or "native")
    log_prefix = f"[{server_id}/{source_name}]"

    while True:
        try:
            if runtime == "docker":
                stream_log_lines = stream_docker_log_lines(client, container_name)
            else:
                stream_log_lines = stream_native_log_lines(log_file_path)

            for message in stream_log_lines:
                if not message:
                    continue

                print(f"{log_prefix} {message}")
                event = parser.parse(message)
                if event:
                    try:
                        notifier.send_presence_event(
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
        except FileNotFoundError:
            print(f"{log_prefix} log file not found")
            time.sleep(3)
        except Exception as e:
            print(f"{log_prefix} log watcher error: {e}")
            time.sleep(3)


def start_log_watchers(client, notifier, servers):
    for server in servers:
        thread = threading.Thread(target=watch_server_logs, args=(client, notifier, server), daemon=True)
        thread.start()
