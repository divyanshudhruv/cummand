import asyncio
import time
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class TunnelSession:
    code: str
    local_port: int
    ws: any
    log_level: str = "info"
    start_time: float = field(default_factory=time.time)
    request_count: int = 0
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
    def tunnel_url(self) -> str:
        return f"/{self.code}"

    def record_request(self):
        self.request_count += 1
