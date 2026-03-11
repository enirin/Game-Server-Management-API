"""Backward-compatible wrappers for legacy imports.

New code should use `games.create_game_plugin` and `games.base.PresenceEvent` directly.
"""

from games.base import PresenceEvent
from games.registry import create_game_plugin


class BaseLogParser:
    def parse(self, line: str):
        raise NotImplementedError


class _ParserAdapter(BaseLogParser):
    def __init__(self, game: str):
        self._plugin = create_game_plugin(game)

    def parse(self, line: str):
        return self._plugin.parse_presence_event(line)


def get_parser(game: str) -> BaseLogParser:
    return _ParserAdapter(game)
