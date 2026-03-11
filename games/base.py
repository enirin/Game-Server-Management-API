import re
from dataclasses import dataclass
from typing import Optional


@dataclass
class PresenceEvent:
    event_type: str
    player_name: str


class GamePlugin:
    ALIASES = set()

    def parse_presence_event(self, line: str) -> Optional[PresenceEvent]:
        return None

    def extract_day(self, logs_text: str) -> int:
        day_match = re.findall(r"Day[:\\s]+(\\d+)", logs_text, re.IGNORECASE)
        return int(day_match[-1]) if day_match else 0
