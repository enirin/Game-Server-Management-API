import re
from typing import Optional

from games.base import GamePlugin, PresenceEvent


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
