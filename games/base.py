import re
from dataclasses import dataclass
from typing import Optional


@dataclass
class PresenceEvent:
    event_type: str
    player_name: str
    source_id: Optional[str] = None


class GamePlugin:
    ALIASES = set()

    def parse_presence_event(self, line: str) -> Optional[PresenceEvent]:
        return None

    def build_presence_prompt(self, server_id: str, event: PresenceEvent) -> str:
        action_map = {
            "login": "ログイン",
            "logout": "ログアウト",
        }
        action = action_map.get(event.event_type, event.event_type)
        return (
            f"システム通知: {server_id} でプレイヤー '{event.player_name}' が{action}しました。"
            f" プレイヤー名を含めて短く案内してください。"
        )

    def extract_day(self, logs_text: str) -> int:
        day_match = re.findall(r"Day[:\\s]+(\\d+)", logs_text, re.IGNORECASE)
        return int(day_match[-1]) if day_match else 0
