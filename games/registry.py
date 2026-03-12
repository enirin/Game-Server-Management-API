from games.default_plugin import DefaultGamePlugin
from games.seven_days_to_die import SevenDaysToDiePlugin
from games.valheim import ValheimPlugin

# 新しいゲームを追加する場合は、games/<plugin_name>/ 配下に plugin.py を追加し、
# ここへクラスを登録します。
PLUGIN_CLASSES = [
    ValheimPlugin,
    SevenDaysToDiePlugin,
]

ALIASES_TO_PLUGIN = {}
for plugin_cls in PLUGIN_CLASSES:
    for alias in plugin_cls.ALIASES:
        ALIASES_TO_PLUGIN[alias] = plugin_cls


def create_game_plugin(game: str):
    normalized = (game or "").strip().lower()
    plugin_cls = ALIASES_TO_PLUGIN.get(normalized)
    if not plugin_cls:
        return DefaultGamePlugin()
    return plugin_cls()


def get_supported_game_aliases():
    return sorted(ALIASES_TO_PLUGIN.keys())
