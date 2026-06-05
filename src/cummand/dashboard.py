import asyncio
import time
from typing import Optional

from rich.console import Console
from rich.text import Text
from rich.style import Style
from rich.live import Live
from rich.layout import Layout

from cummand.tunnel import TunnelSession


def _fmt_bytes(n: int) -> str:
    for unit in ("B", "KB", "MB", "GB"):
        if n < 1024:
            return f"{n:.1f} {unit}"
        n /= 1024
    return f"{n:.1f} TB"


def _fmt_uptime(seconds: float) -> str:
    h, rem = divmod(int(seconds), 3600)
    m, s = divmod(rem, 60)
    if h > 0:
        return f"{h}h {m}m {s}s"
    if m > 0:
        return f"{m}m {s}s"
    return f"{s}s"


def _render(tunnel: TunnelSession, server_url: str) -> Layout:
    tunnel_url = server_url.replace("{code}", tunnel.code)
    lat = tunnel.latency
    lat_str = f"{lat:.0f}ms" if lat > 0 else "—"
    layout = Layout()
    layout.split_column(
        Layout(Text(f" TUNNEL INFO ", style=Style(
            bgcolor="yellow", bold=True, color="black")), size=1),
        Layout(Text.assemble(("Status     ", "white"),
               ("● Online", "green")), size=1),
        Layout(Text.assemble(("Tunnel URL ", "white"),
               (tunnel_url, "dim white")), size=1),
        Layout(Text.assemble(("Uptime     ", "white"),
               (_fmt_uptime(tunnel.uptime), "dim white")), size=1),
        Layout(Text.assemble(("Requests   ", "white"),
               (str(tunnel.request_count), "dim white")), size=1),
        Layout(Text.assemble(("Data       ", "white"),
               (_fmt_bytes(tunnel.bytes_sent), "dim white")), size=1),
        Layout(Text.assemble(("Latency    ", "white"),
               (lat_str, "dim white")), size=1),
    )
    return layout


class Dashboard:
    def __init__(self, tunnel: TunnelSession, server_url: str):
        self.tunnel = tunnel
        self.server_url = server_url
        self.console = Console()
        self._running = False

    def log(self, message: str):
        pass

    async def refresh_loop(self):
        self._running = True
        try:
            with Live(_render(self.tunnel, self.server_url), console=self.console, refresh_per_second=4, transient=True) as live:
                while self._running:
                    live.update(_render(self.tunnel, self.server_url))
                    await asyncio.sleep(1)
        except asyncio.CancelledError:
            pass
        finally:
            self._running = False

    def stop(self):
        self._running = False
