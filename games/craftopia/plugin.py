import json
import re
import sqlite3
from pathlib import Path
from typing import Optional

from games.base import GamePlugin, PresenceEvent, ServerStatusContext


class CraftopiaPlugin(GamePlugin):
    ALIASES = {"craftopia", "craft"}

    _event_pattern = re.compile(
        r"^\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}\s+(LOGIN|LOGOUT)\s+(\S+)",
        re.IGNORECASE,
    )

    def parse_presence_event(self, line: str) -> Optional[PresenceEvent]:
        match = self._event_pattern.search(line.strip())
        if not match:
            return None

        event_type = match.group(1).lower()
        endpoint = match.group(2).strip()
        return PresenceEvent(event_type=event_type, player_name=endpoint, source_id=endpoint)

    def build_presence_prompt(self, server_id: str, event: PresenceEvent) -> str:
        endpoint = event.source_id or event.player_name

        if event.event_type == "login":
            return (
                f"【システム通知】Craftopiaサーバー『{server_id}』に接続元『{endpoint}』のプレイヤーが参加しました。"
                f" 自然で短い歓迎メッセージを作成してください。発話には必ず『{endpoint}』を含めてください。"
            )

        if event.event_type == "logout":
            return (
                f"【システム通知】Craftopiaサーバー『{server_id}』で接続元『{endpoint}』のプレイヤーが退出しました。"
                f" 自然で短いねぎらいメッセージを作成してください。発話には必ず『{endpoint}』を含めてください。"
            )

        return super().build_presence_prompt(server_id, event)

    def extend_server_status(self, status_payload: dict, context: ServerStatusContext) -> dict:
        if context.status == "online":
            day = self._extract_day_from_save(context.server_config)
            if day is not None:
                status_payload["day"] = day

        if context.status != "online" or not context.presence_logs_text:
            return status_payload

        active_players = self._estimate_active_players(context.presence_logs_text)
        max_players = context.server_config["max_players"]
        status_payload["stats"]["players"] = f"{active_players}/{max_players}"
        return status_payload

    def _extract_day_from_save(self, server_config: dict) -> Optional[int]:
        for world_db_path in self._iter_world_db_paths(server_config):
            try:
                with sqlite3.connect(world_db_path) as conn:
                    cursor = conn.cursor()
                    cursor.execute("SELECT value FROM Entity WHERE id = ? LIMIT 1", ("WorldSave",))
                    row = cursor.fetchone()
                    if not row or not row[0]:
                        continue

                payload = json.loads(row[0])
                latest_day = payload.get("latestDay")
                if latest_day is None:
                    continue
                return int(float(latest_day))
            except Exception:
                continue

        return None

    def _iter_world_db_paths(self, server_config: dict):
        seen_paths = set()

        for candidate in self._candidate_save_paths(server_config):
            if not candidate.exists():
                continue

            if candidate.is_file() and candidate.suffix.lower() == ".db":
                resolved = candidate.resolve()
                if resolved not in seen_paths:
                    seen_paths.add(resolved)
                    yield resolved
                continue

            worlds_dir = candidate / "Worlds"
            if not worlds_dir.is_dir():
                continue

            for world_db_path in sorted(worlds_dir.glob("*.db"), key=lambda path: path.stat().st_mtime, reverse=True):
                resolved = world_db_path.resolve()
                if resolved in seen_paths:
                    continue
                seen_paths.add(resolved)
                yield resolved

    def _candidate_save_paths(self, server_config: dict):
        candidates = []

        save_data_path = server_config.get("save_data_path", "")
        if save_data_path:
            candidates.append(Path(save_data_path).expanduser())

        for key in ("presence_log_path", "log_file_path"):
            source_path = server_config.get(key, "")
            if not source_path:
                continue

            source = Path(source_path).expanduser()
            parent_dir = source.parent
            candidates.append(parent_dir / "data")
            candidates.append(parent_dir)

        return candidates

    def _estimate_active_players(self, logs_text: str) -> int:
        active_endpoints = set()

        for line in logs_text.splitlines():
            event = self.parse_presence_event(line)
            if not event:
                continue

            endpoint = event.source_id or event.player_name
            if event.event_type == "login":
                active_endpoints.add(endpoint)
            elif event.event_type == "logout":
                active_endpoints.discard(endpoint)

        return len(active_endpoints)
