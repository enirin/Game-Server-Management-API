from typing import Optional

import requests

from log_parsers import PresenceEvent


class DiscordNotifier:
    def __init__(self, tell_url: str, web_endpoint_token: str = "", timeout_sec: int = 5):
        self.tell_url = tell_url
        self.web_endpoint_token = web_endpoint_token
        self.timeout_sec = timeout_sec

    def _build_prompt(self, server_id: str, game: str, event: PresenceEvent) -> str:
        action_map = {
            "login": "ログイン",
            "logout": "ログアウト",
        }
        action = action_map.get(event.event_type, event.event_type)
        return (
            f"システム通知: {server_id} ({game}) でプレイヤー '{event.player_name}' が{action}しました。"
            f" プレイヤー名を含めて短く案内してください。"
        )

    def send_presence_event(self, server_id: str, game: str, event: PresenceEvent, channel_id: Optional[int]):
        payload = {"prompt": self._build_prompt(server_id=server_id, game=game, event=event)}
        if channel_id is not None:
            payload["channel_id"] = channel_id

        headers = {"Content-Type": "application/json"}
        if self.web_endpoint_token:
            headers["X-Send-Token"] = self.web_endpoint_token

        requests.post(self.tell_url, json=payload, headers=headers, timeout=self.timeout_sec)
