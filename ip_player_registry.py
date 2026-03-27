import ipaddress
import os
import threading
from pathlib import Path


def _default_registry_path() -> Path:
    configured_path = os.getenv("GAME_SERVER_IP_PLAYER_MAP_PATH", "").strip()
    if configured_path:
        return Path(configured_path).expanduser()
    return Path(__file__).resolve().parent / "ip_player_map.txt"


def normalize_ip_address(value: str) -> str:
    raw_value = str(value or "").strip()
    if not raw_value:
        raise ValueError("ip_address must not be empty")

    if raw_value.startswith("[") and "]" in raw_value:
        closing_index = raw_value.index("]")
        candidate = raw_value[1:closing_index]
        return str(ipaddress.ip_address(candidate))

    try:
        return str(ipaddress.ip_address(raw_value))
    except ValueError:
        pass

    if raw_value.count(":") == 1:
        host_part, port_part = raw_value.rsplit(":", 1)
        if port_part.isdigit():
            return str(ipaddress.ip_address(host_part))

    raise ValueError(f"'{value}' is not a valid IP address or IP:port endpoint")


def endpoint_to_ip_address(value: str) -> str:
    raw_value = str(value or "").strip()
    if not raw_value:
        return ""

    try:
        return normalize_ip_address(raw_value)
    except ValueError:
        return raw_value


class IpPlayerRegistry:
    def __init__(self, path: str | Path | None = None):
        self._path = Path(path).expanduser() if path is not None else _default_registry_path()
        self._lock = threading.RLock()

    @property
    def path(self) -> Path:
        return self._path

    def get_player_name(self, ip_address: str) -> str | None:
        normalized_ip = normalize_ip_address(ip_address)
        entries = self._load_entries()
        return entries.get(normalized_ip)

    def set_player_name(self, ip_address: str, player_name: str) -> dict:
        normalized_ip = normalize_ip_address(ip_address)
        normalized_name = str(player_name or "").strip()
        if not normalized_name:
            raise ValueError("player_name must not be empty")

        with self._lock:
            entries = self._load_entries_unlocked()
            entries[normalized_ip] = normalized_name
            self._write_entries_unlocked(entries)

        return {
            "ip_address": normalized_ip,
            "player_name": normalized_name,
            "path": str(self._path),
        }

    def list_entries(self) -> list[dict]:
        entries = self._load_entries()
        return [
            {"ip_address": ip_address, "player_name": player_name}
            for ip_address, player_name in sorted(entries.items())
        ]

    def _load_entries(self) -> dict[str, str]:
        with self._lock:
            return self._load_entries_unlocked()

    def _load_entries_unlocked(self) -> dict[str, str]:
        if not self._path.exists():
            return {}

        entries: dict[str, str] = {}
        with open(self._path, "r", encoding="utf-8") as handle:
            for raw_line in handle:
                line = raw_line.strip()
                if not line or line.startswith("#"):
                    continue

                if "\t" in line:
                    ip_part, player_name = line.split("\t", 1)
                elif "=" in line:
                    ip_part, player_name = line.split("=", 1)
                else:
                    continue

                try:
                    normalized_ip = normalize_ip_address(ip_part)
                except ValueError:
                    continue

                normalized_name = player_name.strip()
                if not normalized_name:
                    continue
                entries[normalized_ip] = normalized_name
        return entries

    def _write_entries_unlocked(self, entries: dict[str, str]) -> None:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        temp_path = self._path.with_suffix(self._path.suffix + ".tmp")
        with open(temp_path, "w", encoding="utf-8") as handle:
            handle.write("# IP to player name mappings\n")
            for ip_address, player_name in sorted(entries.items()):
                handle.write(f"{ip_address}\t{player_name}\n")
        os.replace(temp_path, self._path)