import re
from typing import Dict, Optional

from games.base import GamePlugin, PresenceEvent


class ValheimPlugin(GamePlugin):
    ALIASES = {"valheim"}

    def __init__(self):
        self._pending_steam_id: Optional[str] = None
        self._steam_to_name: Dict[str, str] = {}
        self._steam_id_pattern = re.compile(r"SteamID\s+(\d+)", re.IGNORECASE)
        self._closing_socket_pattern = re.compile(r"Closing socket\s+(\d+)", re.IGNORECASE)

    def parse_presence_event(self, line: str) -> Optional[PresenceEvent]:
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
