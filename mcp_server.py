import json
import logging
import os

from mcp.server.fastmcp import FastMCP

from config_loader import load_config
from management_service import ManagementError, ManagementService


LOGGER = logging.getLogger(__name__)
BASE_DIR = os.path.dirname(__file__)
CONFIG_PATH = os.getenv("GAME_SERVER_CONFIG_PATH", os.path.join(BASE_DIR, "config.yaml"))


def _env_bool(name: str, default: bool) -> bool:
    raw_value = os.getenv(name)
    if raw_value is None:
        return default
    return raw_value.strip().lower() in {"true", "1", "yes", "on"}


CONFIG = load_config(CONFIG_PATH)
MCP_CONFIG = CONFIG["mcp"]
MCP_HOST = os.getenv("MCP_HOST", MCP_CONFIG["host"])
MCP_PORT = int(os.getenv("MCP_PORT", str(MCP_CONFIG["port"])))
MCP_PATH = os.getenv("MCP_PATH", MCP_CONFIG["path"])
MCP_JSON_RESPONSE = _env_bool("MCP_JSON_RESPONSE", MCP_CONFIG["json_response"])
MCP_STATELESS_HTTP = _env_bool("MCP_STATELESS_HTTP", MCP_CONFIG["stateless_http"])


def _build_service() -> ManagementService:
    return ManagementService(CONFIG["servers"], base_dir=BASE_DIR)


service = _build_service()
mcp = FastMCP(
    "Game Server Management API",
    host=MCP_HOST,
    port=MCP_PORT,
    streamable_http_path=MCP_PATH,
    json_response=MCP_JSON_RESPONSE,
    stateless_http=MCP_STATELESS_HTTP,
)


def _handle_tool_error(error: ManagementError) -> dict:
    return error.to_payload()


def _internal_error_payload(message: str) -> dict:
    return {
        "error": {
            "code": "internal_error",
            "message": message,
            "details": {},
        }
    }


def _json_text(payload: dict) -> str:
    return json.dumps(payload, ensure_ascii=False, indent=2)


@mcp.tool()
def list_servers() -> dict:
    """List all managed servers with their current status."""
    try:
        return service.list_servers()
    except Exception as error:
        return _internal_error_payload(str(error))


@mcp.tool()
def get_server_status(server_id: str) -> dict:
    """Get the current status for a single managed server."""
    try:
        return service.get_server_status(server_id)
    except ManagementError as error:
        return _handle_tool_error(error)
    except Exception as error:
        return _internal_error_payload(str(error))


@mcp.tool()
def start_server(server_id: str) -> dict:
    """Start a managed server. Clients should require explicit confirmation before calling this tool."""
    try:
        return service.start_server(server_id)
    except ManagementError as error:
        return _handle_tool_error(error)
    except Exception as error:
        return _internal_error_payload(str(error))


@mcp.tool()
def stop_server(server_id: str) -> dict:
    """Stop a managed server. Clients should require explicit confirmation before calling this tool."""
    try:
        return service.stop_server(server_id)
    except ManagementError as error:
        return _handle_tool_error(error)
    except Exception as error:
        return _internal_error_payload(str(error))


@mcp.tool()
def get_server_maintenance_notes(server_id: str) -> dict:
    """Return the maintenance notes for the server's game."""
    try:
        return service.get_server_maintenance_notes(server_id)
    except ManagementError as error:
        return _handle_tool_error(error)
    except Exception as error:
        return _internal_error_payload(str(error))


@mcp.resource("servers://catalog")
def servers_catalog() -> str:
    """Static catalog of the managed servers."""
    try:
        return _json_text(service.get_server_catalog())
    except Exception as error:
        return _json_text(_internal_error_payload(str(error)))


@mcp.resource("servers://status")
def servers_status() -> str:
    """Current status for all managed servers."""
    try:
        return _json_text(service.list_servers())
    except Exception as error:
        return _json_text(_internal_error_payload(str(error)))


@mcp.resource("servers://status/{server_id}")
def server_status_resource(server_id: str) -> str:
    """Current status for a single managed server."""
    try:
        return _json_text(service.get_server_status(server_id))
    except ManagementError as error:
        return _json_text(error.to_payload())
    except Exception as error:
        return _json_text(_internal_error_payload(str(error)))


@mcp.resource("games://maintenance/{game}")
def game_maintenance_resource(game: str) -> str:
    """Maintenance notes for a managed game."""
    try:
        return service.get_game_maintenance_notes(game)["content"]
    except ManagementError as error:
        return _json_text(error.to_payload())
    except Exception as error:
        return _json_text(_internal_error_payload(str(error)))


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    LOGGER.info("Starting MCP server on http://%s:%s%s", MCP_HOST, MCP_PORT, MCP_PATH)
    mcp.run(transport="streamable-http")


if __name__ == "__main__":
    main()