"""Tunnel session dataclass — tracks tunnel metadata and state."""

import asyncio
import time
from dataclasses import dataclass, field

import websockets


MAX_MSG_SIZE: int = 20 * 1024 * 1024


@dataclass
class TunnelSession:
    """Holds the state and metrics for an active tunnel connection."""
    code: str
    local_port: int
    ws: websockets.ClientConnection
    log_level: str = "info"
    start_time: float = field(default_factory=time.time)
    request_count: int = 0
    bytes_sent: int = 0
    pending: dict[str, asyncio.Future] = field(default_factory=dict)
    _latency: float = 0.0

    @property
    def uptime(self) -> float:
        return time.time() - self.start_time

    @property
    def latency(self) -> float:
        return self._latency

    @latency.setter
    def latency(self, value: float):
        self._latency = value

    @property
    def tunnel_path(self) -> str:
        return f"/{self.code}"

    def record_request(self) -> None:
        self.request_count += 1
