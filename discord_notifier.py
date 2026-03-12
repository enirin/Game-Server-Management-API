import requests


class DiscordNotifier:
    def __init__(self, tell_url: str, web_endpoint_token: str = "", timeout_sec: int = 5):
        self.tell_url = tell_url
        self.web_endpoint_token = web_endpoint_token
        self.timeout_sec = timeout_sec

    def send_prompt(self, prompt: str, channel_id=None):
        payload = {"prompt": prompt}
        if channel_id is not None:
            payload["channel_id"] = channel_id

        headers = {"Content-Type": "application/json"}
        if self.web_endpoint_token:
            headers["X-Send-Token"] = self.web_endpoint_token

        requests.post(self.tell_url, json=payload, headers=headers, timeout=self.timeout_sec)
