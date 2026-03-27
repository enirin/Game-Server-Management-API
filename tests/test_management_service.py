import unittest
from unittest.mock import patch

from management_service import ConfigurationError, ManagementService, ServerNotFoundError


class ManagementServiceTest(unittest.TestCase):
    def setUp(self):
        self.servers = [
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
        ]
        self.service = ManagementService(self.servers, base_dir="/home/enirin/work/Game-Server-Management-API")

    @patch("management_service.build_server_status")
    def test_list_servers_builds_payload_for_all_servers(self, build_server_status_mock):
        build_server_status_mock.return_value = {"name": "craftopia", "status": "online"}

        result = self.service.list_servers()

        self.assertEqual({"servers": [{"name": "craftopia", "status": "online"}]}, result)
        build_server_status_mock.assert_called_once_with(self.servers[0])

    def test_get_server_status_raises_for_unknown_server(self):
        with self.assertRaises(ServerNotFoundError):
            self.service.get_server_status("missing")

    @patch("management_service.start_server_instance")
    def test_start_server_maps_runtime_config_errors(self, start_server_instance_mock):
        start_server_instance_mock.return_value = (
            {
                "success": False,
                "message": "Container 'craftopia-server' not found",
                "server_name": "craftopia",
            },
            404,
        )

        with self.assertRaises(ConfigurationError) as context:
            self.service.start_server("craftopia")

        self.assertEqual("configuration_error", context.exception.error_code)

    def test_get_server_maintenance_notes_reads_real_document(self):
        result = self.service.get_server_maintenance_notes("craftopia")

        self.assertEqual("craftopia", result["server_id"])
        self.assertEqual("craftopia", result["game"])
        self.assertTrue(result["path"].endswith("games/craftopia/MAINTENANCE.md"))
        self.assertIn("Craftopia", result["content"])


if __name__ == "__main__":
    unittest.main()