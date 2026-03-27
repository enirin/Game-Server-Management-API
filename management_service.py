import inspect
import os
from http import HTTPStatus
from typing import Any

from games import create_game_plugin
from server_runtime import build_server_status, start_server_instance, stop_server_instance


class ManagementError(Exception):
    error_code = "internal_error"
    status_code = HTTPStatus.INTERNAL_SERVER_ERROR

    def __init__(self, message: str, details: dict[str, Any] | None = None):
        super().__init__(message)
        self.message = message
        self.details = details or {}

    def to_payload(self) -> dict[str, Any]:
        return {
            "error": {
                "code": self.error_code,
                "message": self.message,
                "details": self.details,
            }
        }


class ServerNotFoundError(ManagementError):
    error_code = "not_found"
    status_code = HTTPStatus.NOT_FOUND


class RuntimeUnavailableError(ManagementError):
    error_code = "runtime_unavailable"
    status_code = HTTPStatus.SERVICE_UNAVAILABLE


class InvalidServerStateError(ManagementError):
    error_code = "invalid_state"
    status_code = HTTPStatus.CONFLICT


class ConfigurationError(ManagementError):
    error_code = "configuration_error"
    status_code = HTTPStatus.BAD_REQUEST


class InternalManagementError(ManagementError):
    error_code = "internal_error"
    status_code = HTTPStatus.INTERNAL_SERVER_ERROR


class ManagementService:
    def __init__(self, servers: list[dict[str, Any]], base_dir: str | None = None):
        self._servers = list(servers)
        self._servers_by_id = {server["server_id"]: server for server in self._servers}
        self._base_dir = base_dir or os.path.dirname(__file__)

    def list_servers(self) -> dict[str, list[dict[str, Any]]]:
        return {"servers": [build_server_status(server) for server in self._servers]}

    def get_server_catalog(self) -> dict[str, list[dict[str, Any]]]:
        servers = []
        for server in self._servers:
            servers.append(
                {
                    "server_id": server["server_id"],
                    "server_aliases": server["server_aliases"],
                    "game": server["game"],
                    "runtime": server["runtime"],
                    "address": server["address"],
                    "max_players": server["max_players"],
                }
            )
        return {"servers": servers}

    def get_server_status(self, server_id: str) -> dict[str, dict[str, Any]]:
        server = self._get_server(server_id)
        return {"server": build_server_status(server)}

    def start_server(self, server_id: str) -> dict[str, Any]:
        server = self._get_server(server_id)
        payload, status_code = start_server_instance(server_id, server)
        self._raise_for_operation_error(server_id, payload, status_code)
        return payload

    def stop_server(self, server_id: str) -> dict[str, Any]:
        server = self._get_server(server_id)
        payload, status_code = stop_server_instance(server_id, server)
        self._raise_for_operation_error(server_id, payload, status_code)
        return payload

    def get_server_maintenance_notes(self, server_id: str) -> dict[str, Any]:
        server = self._get_server(server_id)
        notes = self.get_game_maintenance_notes(server["game"])
        return {
            "server_id": server_id,
            "game": notes["game"],
            "path": notes["path"],
            "content": notes["content"],
        }

    def get_game_maintenance_notes(self, game: str) -> dict[str, str]:
        maintenance_path = self._resolve_maintenance_path(game)
        try:
            with open(maintenance_path, "r", encoding="utf-8") as handle:
                content = handle.read()
        except FileNotFoundError as exc:
            raise ConfigurationError(
                f"Maintenance notes for game '{game}' are not available",
                details={"game": game, "path": self._relative_to_base(maintenance_path)},
            ) from exc

        return {
            "game": game,
            "path": self._relative_to_base(maintenance_path),
            "content": content,
        }

    def _get_server(self, server_id: str) -> dict[str, Any]:
        server = self._servers_by_id.get(server_id)
        if server:
            return server
        raise ServerNotFoundError(
            f"Server '{server_id}' not found",
            details={"server_id": server_id},
        )

    def _resolve_maintenance_path(self, game: str) -> str:
        plugin = create_game_plugin(game)
        plugin_file = inspect.getfile(plugin.__class__)
        maintenance_path = os.path.join(os.path.dirname(plugin_file), "MAINTENANCE.md")
        return maintenance_path

    def _relative_to_base(self, path: str) -> str:
        return os.path.relpath(path, self._base_dir)

    def _raise_for_operation_error(
        self,
        server_id: str,
        payload: dict[str, Any],
        status_code: int,
    ) -> None:
        if 200 <= status_code < 300:
            return

        message = str(payload.get("message") or f"Server '{server_id}' operation failed")
        details = {
            "server_id": server_id,
            "status_code": status_code,
        }
        error_class = self._map_operation_error(status_code, message)
        raise error_class(message, details=details)

    def _map_operation_error(self, status_code: int, message: str) -> type[ManagementError]:
        lowered_message = message.lower()

        if status_code == HTTPStatus.SERVICE_UNAVAILABLE:
            return RuntimeUnavailableError
        if status_code == HTTPStatus.NOT_FOUND and lowered_message.startswith("server '"):
            return ServerNotFoundError
        if status_code == HTTPStatus.NOT_FOUND and "container" in lowered_message:
            return ConfigurationError
        if status_code == HTTPStatus.BAD_REQUEST:
            return ConfigurationError
        if "already running" in lowered_message or "already stopped" in lowered_message:
            return InvalidServerStateError
        return InternalManagementError