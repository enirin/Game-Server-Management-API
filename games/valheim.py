import re
from typing import Dict, Optional, List

from games.base import GamePlugin, PresenceEvent


class ValheimPlugin(GamePlugin):
    """Valheimサーバーのログを解析してプレイヤー情報を管理するプラグイン"""
    ALIASES = {"valheim"}

    def __init__(self):
        self._pending_steam_id: Optional[str] = None
        self._steam_to_name: Dict[str, str] = {}
        # SteamIDと内部IDの紐付けが必要な場合のためのバックアップ
        self._name_to_steam = {} 
        
        self._steam_id_pattern = re.compile(r"SteamID\s+(\d+)", re.IGNORECASE)
        # 複数のログアウトパターンに対応
        self._logout_patterns = [
            re.compile(r"Closing socket\s+(\d+)", re.IGNORECASE),
            re.compile(r"Disconnecting\s+(\d+)", re.IGNORECASE),
            re.compile(r"Destroying object for\s+(.+)", re.IGNORECASE)
        ]

    def get_player_count(self) -> int:
        return len(self._steam_to_name)

    def get_player_names(self) -> List[str]:
        return list(self._steam_to_name.values())

    def parse_presence_event(self, line: str) -> Optional[PresenceEvent]:
        # --- 1. 接続開始 (SteamID) ---
        if "Got connection SteamID" in line:
            match = self._steam_id_pattern.search(line)
            if match:
                self._pending_steam_id = match.group(1)
            return None

        # --- 2. ログイン確定 (Character Name) ---
        if "Got character ZDOID from" in line:
            try:
                name_part = line.split("from", 1)[-1].strip()
                player_name = name_part.split(":", 1)[0].strip()
                
                if player_name and self._pending_steam_id:
                    self._steam_to_name[self._pending_steam_id] = player_name
                    self._name_to_steam[player_name] = self._pending_steam_id
                    sid = self._pending_steam_id
                    self._pending_steam_id = None
                    return PresenceEvent(event_type="login", player_name=player_name)
            except Exception:
                pass
            return None

        # --- 3. 切断検知 (Closing / Disconnecting) ---
        # 複数のパターンでチェック
        for pattern in self._logout_patterns:
            match = pattern.search(line)
            if not match:
                continue
                
            target = match.group(1).strip()
            
            # IDによる削除
            if target in self._steam_to_name:
                player_name = self._steam_to_name.pop(target)
                self._name_to_steam.pop(player_name, None)
                return PresenceEvent(event_type="logout", player_name=player_name)
            
            # 名前による削除 (Destroying object for パターン用)
            if target in self._name_to_steam:
                sid = self._name_to_steam.pop(target)
                player_name = self._steam_to_name.pop(sid, target)
                return PresenceEvent(event_type="logout", player_name=player_name)

        # セーフティ：サーバーが完全に空になるログが出た場合などはここで全クリアしても良い
        if "ZNet shutdown" in line or "Net manager stopped" in line:
            self._steam_to_name.clear()
            self._name_to_steam.clear()

        return None

    def extract_day(self, logs: str) -> int:
        """ログから最新の日数を抽出"""
        day_match = re.findall(r"Day\s+(\d+)", logs, re.IGNORECASE)
        return int(day_match[-1]) if day_match else 0