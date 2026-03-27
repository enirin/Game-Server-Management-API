import tempfile
import unittest
from unittest.mock import patch

from games.craftopia.plugin import CraftopiaPlugin
from ip_player_registry import IpPlayerRegistry


class CraftopiaPluginTest(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.registry = IpPlayerRegistry(f"{self.temp_dir.name}/ip-player-map.txt")

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_parse_presence_event_resolves_registered_player_name(self):
        self.registry.set_player_name("203.0.113.10", "Alice")

        with patch("games.craftopia.plugin.IpPlayerRegistry", return_value=self.registry):
            plugin = CraftopiaPlugin()
            event = plugin.parse_presence_event("2026-03-23 21:14:55 LOGIN 203.0.113.10:54000")

        self.assertIsNotNone(event)
        self.assertEqual("login", event.event_type)
        self.assertEqual("Alice", event.player_name)
        self.assertEqual("203.0.113.10", event.source_id)

    def test_parse_presence_event_falls_back_to_ip_without_port(self):
        with patch("games.craftopia.plugin.IpPlayerRegistry", return_value=self.registry):
            plugin = CraftopiaPlugin()
            event = plugin.parse_presence_event("2026-03-23 21:14:55 LOGOUT 203.0.113.10:54000 idle=8s")

        self.assertIsNotNone(event)
        self.assertEqual("logout", event.event_type)
        self.assertEqual("203.0.113.10", event.player_name)
        self.assertEqual("203.0.113.10", event.source_id)

    def test_build_presence_prompt_uses_resolved_player_name(self):
        self.registry.set_player_name("203.0.113.10", "Alice")

        with patch("games.craftopia.plugin.IpPlayerRegistry", return_value=self.registry):
            plugin = CraftopiaPlugin()
            event = plugin.parse_presence_event("2026-03-23 21:14:55 LOGIN 203.0.113.10:54000")

        prompt = plugin.build_presence_prompt("craftopia", event)

        self.assertIn("Alice", prompt)
        self.assertNotIn("54000", prompt)


if __name__ == "__main__":
    unittest.main()