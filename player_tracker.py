import threading
from typing import List

class PlayerTracker:
    """スレッドセーフなプレイヤー管理クラス"""
    def __init__(self):
        self._lock = threading.Lock()
        # { server_id: { player_name1, player_name2, ... } }
        self._servers_players = {}

    def add_player(self, server_id: str, player_name: str):
        """プレイヤーを追加する"""
        with self._lock:
            if server_id not in self._servers_players:
                self._servers_players[server_id] = set()
            self._servers_players[server_id].add(player_name)

    def remove_player(self, server_id: str, player_name: str):
        """プレイヤーを削除する"""
        with self._lock:
            if server_id in self._servers_players:
                self._servers_players[server_id].discard(player_name)

    def get_players(self, server_id: str) -> List[str]:
        """現在ログイン中のプレイヤー名のリストを取得する"""
        with self._lock:
            if server_id in self._servers_players:
                return list(self._servers_players[server_id])
            return []

    def clear_players(self, server_id: str):
        """指定サーバーのプレイヤーリストをクリアする（サーバー停止時など）"""
        with self._lock:
            if server_id in self._servers_players:
                self._servers_players[server_id].clear()

# グローバルインスタンス
tracker = PlayerTracker()
