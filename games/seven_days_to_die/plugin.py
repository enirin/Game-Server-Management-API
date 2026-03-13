import re
from typing import Optional

from games.base import GamePlugin, PresenceEvent, ServerStatusContext


class SevenDaysToDiePlugin(GamePlugin):
    ALIASES = {"7dtd", "7d2d", "7days2die", "7daystodie", "seven_days_to_die", "sevendaystodie"}

    def parse_presence_event(self, line: str) -> Optional[PresenceEvent]:
        login_patterns = [
            r"Player '([^']+)' joined the game",
        ]
        logout_patterns = [
            r"Player '([^']+)' left the game",
        ]
        die_patterns = [
            r"Player '([^']+)' died",
        ]

        for pattern in login_patterns:
            match = re.search(pattern, line, re.IGNORECASE)
            if match:
                return PresenceEvent(event_type="login", player_name=match.group(1).strip())

        for pattern in logout_patterns:
            match = re.search(pattern, line, re.IGNORECASE)
            if match:
                return PresenceEvent(event_type="logout", player_name=match.group(1).strip())

        for pattern in die_patterns:
            match = re.search(pattern, line, re.IGNORECASE)
            if match:
                return PresenceEvent(event_type="died", player_name=match.group(1).strip())

        return None

    def build_presence_prompt(self, server_id: str, event: PresenceEvent) -> str:
        if event.event_type == "login":
            return (
                f"【システム通知】7 Days to Dieサーバー『{server_id}』に『{event.player_name}』が参加しました。"
                f" 自然で短い歓迎メッセージを作成してください。発話には必ず『{event.player_name}』を含めてください。"
            )

        if event.event_type == "logout":
            return (
                f"【システム通知】7 Days to Dieサーバー『{server_id}』で『{event.player_name}』が退出しました。"
                f" 自然で短いねぎらいメッセージを作成してください。発話には必ず『{event.player_name}』を含めてください。"
            )

        if event.event_type == "died":
            return (
                f"【システム通知】7 Days to Dieサーバー『{server_id}』で『{event.player_name}』が死亡しました。"
                f" ゾンビに倒されたことを揶揄するような、短くウィットに富んだ煽り気味のメッセージを作成してください。"
                f" 発話には必ず『{event.player_name}』を含めてください。"
            )

        return super().build_presence_prompt(server_id, event)

    def extend_server_status(self, status_payload: dict, context: ServerStatusContext) -> dict:
        if context.status != "online" or not context.logs_text:
            return status_payload

        active_players = self._estimate_active_players(context.logs_text)
        max_players = context.server_config["max_players"]
        status_payload["stats"]["players"] = f"{active_players}/{max_players}"
        return status_payload

    def _estimate_active_players(self, logs_text: str) -> int:
        active_players = set()

        for line in logs_text.splitlines():
            event = self.parse_presence_event(line)
            if not event:
                continue

            if event.event_type == "login":
                active_players.add(event.player_name)
            elif event.event_type == "logout":
                active_players.discard(event.player_name)

        return len(active_players)
