import importlib
import inspect
import pkgutil
from pathlib import Path

from games.base import GamePlugin
from games.default_plugin import DefaultGamePlugin


def _discover_plugin_classes():
    plugin_classes = []
    package_dir = Path(__file__).resolve().parent

    for module_info in pkgutil.iter_modules([str(package_dir)]):
        if not module_info.ispkg:
            continue

        module = importlib.import_module(f"games.{module_info.name}.plugin")
        for _, obj in inspect.getmembers(module, inspect.isclass):
            if obj is GamePlugin:
                continue
            if not issubclass(obj, GamePlugin):
                continue
            if obj.__module__ != module.__name__:
                continue
            plugin_classes.append(obj)

    return plugin_classes


PLUGIN_CLASSES = _discover_plugin_classes()


def _build_alias_map(plugin_classes):
    aliases_to_plugin = {}
    for plugin_cls in plugin_classes:
        for alias in plugin_cls.ALIASES:
            normalized_alias = str(alias).strip().lower()
            if not normalized_alias:
                continue
            existing = aliases_to_plugin.get(normalized_alias)
            if existing and existing is not plugin_cls:
                raise ValueError(
                    f"Duplicate game alias '{normalized_alias}' declared by "
                    f"{existing.__name__} and {plugin_cls.__name__}"
                )
            aliases_to_plugin[normalized_alias] = plugin_cls
    return aliases_to_plugin


ALIASES_TO_PLUGIN = _build_alias_map(PLUGIN_CLASSES)


def create_game_plugin(game: str):
    normalized = (game or "").strip().lower()
    plugin_cls = ALIASES_TO_PLUGIN.get(normalized)
    if not plugin_cls:
        return DefaultGamePlugin()
    return plugin_cls()


def get_supported_game_aliases():
    return sorted(ALIASES_TO_PLUGIN.keys())
