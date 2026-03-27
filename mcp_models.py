from typing import Literal, TypedDict


class ServerStats(TypedDict):
    players: str
    cpu: float
    memory: float


class ServerStatus(TypedDict):
    name: str
    server_aliases: list[str]
    status: Literal["online", "offline", "busy"]
    address: str
    stats: ServerStats
    day: int


class ServerCatalogEntry(TypedDict):
    server_id: str
    server_aliases: list[str]
    game: str
    runtime: Literal["docker", "native"]
    address: str
    max_players: int


class OperationResult(TypedDict):
    success: bool
    message: str
    server_name: str


class MaintenanceNotes(TypedDict):
    server_id: str
    game: str
    path: str
    content: str


class ErrorBody(TypedDict):
    code: str
    message: str
    details: dict


class ErrorPayload(TypedDict):
    error: ErrorBody