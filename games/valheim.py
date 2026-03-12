import re
from typing import Dict, Optional, List

from games.base import GamePlugin, PresenceEvent


class ValheimPlugin(GamePlugin):
    ALIASES = {"valheim"}

    def __init__(self):
        self._pending_steam_id: Optional[str] = None
        self._steam_to_name: Dict[str, str] = {}
        self._steam_id_pattern = re.compile(r"SteamID\s+(\d+)", re.IGNORECASE)
        self._closing_socket_pattern = re.compile(r"Closing socket\s+(\d+)", re.IGNORECASE)

    def get_player_count(self) -> int:
        """現在名簿に載っている人数を返す"""
        return len(self._steam_to_name)

    def get_player_names(self) -> List[str]:
        """現在名簿に載っているプレイヤー名のリストを返す"""
        return list(self._steam_to_name.values())

    def parse_presence_event(self, line: str) -> Optional[PresenceEvent]:
        # --- 1. SteamIDの保持 ---
        if "Got connection SteamID" in line:
            match = self._steam_id_pattern.search(line)
            if match:
                self._pending_steam_id = match.group(1)
            return None

        # --- 2. 名前とIDの紐付け ---
        if "Got character ZDOID from" in line:
            try:
                name_part = line.split("from", 1)[-1].strip()
                player_name = name_part.split(":", 1)[0].strip()
                
                if player_name and self._pending_steam_id:
                    self._steam_to_name[self._pending_steam_id] = player_name
                    self._pending_steam_id = None
                    return PresenceEvent(event_type="login", player_name=player_name)
            except Exception:
                pass
            return None

        # --- 3. ログアウト検知 ---
        if "Closing socket" in line:
            match = self._closing_socket_pattern.search(line)
            if match:
                steam_id = match.group(1)
                player_name = self._steam_to_name.pop(steam_id, None)
                if player_name:
                    return PresenceEvent(event_type="logout", player_name=player_name)

        return None

    def extract_day(self, logs: str) -> int:
        """ログから最新の日数を抽出"""
        day_match = re.findall(r"Day\s+(\d+)", logs, re.IGNORECASE)
        return int(day_match[-1]) if day_match else 0