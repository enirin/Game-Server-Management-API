import re
from dataclasses import dataclass
from typing import Dict, Optional


@dataclass
class PresenceEvent:
    event_type: str
    player_name: str


class BaseLogParser:
    def parse(self, line: str) -> Optional[PresenceEvent]:
        raise NotImplementedError


class ValheimLogParser(BaseLogParser):
    def __init__(self):
        self._pending_steam_id: Optional[str] = None
        self._steam_to_name: Dict[str, str] = {}
        self._steam_id_pattern = re.compile(r"SteamID\s+(\d+)", re.IGNORECASE)
        self._closing_socket_pattern = re.compile(r"Closing socket\s+(\d+)", re.IGNORECASE)

    def parse(self, line: str) -> Optional[PresenceEvent]:
        if "Got connection SteamID" in line:
            match = self._steam_id_pattern.search(line)
            if match:
                self._pending_steam_id = match.group(1)
            return None

        if "Got character ZDOID from" in line:
            try:
                name_part = line.split("from", 1)[-1].strip()
                player_name = name_part.split(":", 1)[0].strip()
            except Exception:
                return None

            # SteamIDとの対応が取れたときのみログイン確定にする。
            if not player_name or not self._pending_steam_id:
                return None

            self._steam_to_name[self._pending_steam_id] = player_name
            self._pending_steam_id = None
            return PresenceEvent(event_type="login", player_name=player_name)

        if "Closing socket" in line:
            match = self._closing_socket_pattern.search(line)
            if not match:
                return None

            steam_id = match.group(1)
            player_name = self._steam_to_name.pop(steam_id, None)
            if not player_name:
                return None
            return PresenceEvent(event_type="logout", player_name=player_name)

        return None


class SevenDaysToDieLogParser(BaseLogParser):
    def parse(self, line: str) -> Optional[PresenceEvent]:
        # Examples targeted:
        # "Player connected, entityid=171, name=Bob, steamid=..."
        # "Player disconnected: Bob"
        # "INF GMSG: Player 'Bob' joined the game"
        # "INF GMSG: Player 'Bob' left the game"
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
                player_name = match.group(1).strip()
                player_name = player_name.split(" (")[0].strip()
                return PresenceEvent(event_type="logout", player_name=player_name)

        return None


class NullLogParser(BaseLogParser):
    def parse(self, line: str) -> Optional[PresenceEvent]:
        return None


def get_parser(game: str) -> BaseLogParser:
    normalized = (game or "").strip().lower()
    if normalized in {"valheim"}:
        return ValheimLogParser()
    if normalized in {"7dtd", "7d2d", "7days2die", "7daystodie", "seven_days_to_die", "sevendaystodie"}:
        return SevenDaysToDieLogParser()
    return NullLogParser()
