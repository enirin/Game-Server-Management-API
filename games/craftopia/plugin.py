import re
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
        if context.status != "online" or not context.presence_logs_text:
            return status_payload

        active_players = self._estimate_active_players(context.presence_logs_text)
        max_players = context.server_config["max_players"]
        status_payload["stats"]["players"] = f"{active_players}/{max_players}"
        return status_payload

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
