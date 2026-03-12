import unittest
from player_tracker import PlayerTracker

class TestPlayerTracker(unittest.TestCase):
    def setUp(self):
        self.tracker = PlayerTracker()

    def test_add_remove_player(self):
        self.tracker.add_player("server1", "Alice")
        self.tracker.add_player("server1", "Bob")
        self.assertCountEqual(self.tracker.get_players("server1"), ["Alice", "Bob"])

        self.tracker.remove_player("server1", "Alice")
        self.assertCountEqual(self.tracker.get_players("server1"), ["Bob"])

        self.tracker.remove_player("server1", "Charlie") # Non-existent player
        self.assertCountEqual(self.tracker.get_players("server1"), ["Bob"])

    def test_clear_players(self):
        self.tracker.add_player("server1", "Alice")
        self.tracker.add_player("server1", "Bob")
        self.tracker.clear_players("server1")
        self.assertEqual(len(self.tracker.get_players("server1")), 0)

    def test_multiple_servers(self):
        self.tracker.add_player("server1", "Alice")
        self.tracker.add_player("server2", "Charlie")
        
        self.assertCountEqual(self.tracker.get_players("server1"), ["Alice"])
        self.assertCountEqual(self.tracker.get_players("server2"), ["Charlie"])

if __name__ == '__main__':
    unittest.main()
