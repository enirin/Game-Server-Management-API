import re
from typing import Optional

from ..base import GamePlugin, PresenceEvent


class SevenDaysToDiePlugin(GamePlugin):
    ALIASES = {"7dtd", "7d2d", "7days2die", "7daystodie", "seven_days_to_die", "sevendaystodie"}

    def parse_presence_event(self, line: str) -> Optional[PresenceEvent]:
        login_patterns = [
            r"Player connected.*name=([^,]+)",
            r"Player '([^']+)' joined the game",
        ]
        logout_patterns = [
            r"Player disconnected:?\s*([^,\s].*)",
            r"Player '([^']+)' left the game",
        ]

        for pattern in login_patterns:
            match = re.search(pattern, line, re.IGNORECASE)
            if match:
                return PresenceEvent(event_type="login", player_name=match.group(1).strip())

        for pattern in logout_patterns:
            match = re.search(pattern, line, re.IGNORECASE)
            if match:
                player_name = match.group(1).strip().split(" (")[0].strip()
                return PresenceEvent(event_type="logout", player_name=player_name)

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

        return super().build_presence_prompt(server_id, event)
