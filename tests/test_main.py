import importlib
import importlib.util
import sys
import unittest
from unittest.mock import MagicMock, patch

from management_service import ServerNotFoundError


SAMPLE_CONFIG = {
    "servers": [
        {
            "server_id": "craftopia",
            "server_aliases": ["cp"],
            "game": "craftopia",
            "runtime": "docker",
            "container_name": "craftopia-server",
            "address": "127.0.0.1:6587",
            "max_players": 8,
            "log_file_path": "",
            "presence_log_path": "",
            "process_name": "",
            "status_command": "",
            "start_command": "",
            "stop_command": "",
            "save_data_path": "",
        }
    ],
    "discord": {
        "tell_url": "http://127.0.0.1:5050/tell",
        "web_endpoint_token": "",
        "request_timeout_sec": 5,
    },
    "api": {"port": 5000},
}


@unittest.skipUnless(importlib.util.find_spec("flask") is not None, "Flask is not installed")
class MainRoutesTest(unittest.TestCase):
    def _load_main_module(self, service_mock):
        sys.modules.pop("main", None)
        with (
            patch("config_loader.load_config", return_value=SAMPLE_CONFIG),
            patch("management_service.ManagementService", return_value=service_mock),
            patch("discord_notifier.DiscordNotifier"),
        ):
            module = importlib.import_module("main")
        return module

    def test_list_route_uses_management_service(self):
        service_mock = MagicMock()
        service_mock.list_servers.return_value = {"servers": [{"name": "craftopia"}]}
        main_module = self._load_main_module(service_mock)

        response = main_module.app.test_client().get("/list")

        self.assertEqual(200, response.status_code)
        self.assertEqual({"servers": [{"name": "craftopia"}]}, response.get_json())

    def test_start_route_returns_json_error_for_missing_server(self):
        service_mock = MagicMock()
        service_mock.start_server.side_effect = ServerNotFoundError(
            "Server 'missing' not found",
            details={"server_id": "missing"},
        )
        main_module = self._load_main_module(service_mock)

        response = main_module.app.test_client().post("/start/missing")

        self.assertEqual(404, response.status_code)
        self.assertEqual(
            {"success": False, "message": "Server 'missing' not found"},
            response.get_json(),
        )


if __name__ == "__main__":
    unittest.main()