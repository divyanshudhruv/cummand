import asyncio
import time
from datetime import datetime
from typing import Optional

from rich.layout import Layout
from rich.panel import Panel
from rich.table import Table
from rich.live import Live
from rich.console import Console
from rich.text import Text
from rich import box

from cummand.tunnel import TunnelSession


class Dashboard:
    def __init__(self, tunnel: TunnelSession, server_url: str):
        self.tunnel = tunnel
        self.server_url = server_url
        self.console = Console()
        self.logs: list[str] = []
        self._live: Optional[Live] = None

    def log(self, message: str):
        ts = datetime.now().strftime("%H:%M:%S")
        line = f"[{ts}] {message}"
        self.logs.append(line)
        if len(self.logs) > 100:
            self.logs.pop(0)

    def _build_status_table(self) -> Table:
        t = Table(show_header=False, box=box.SIMPLE, padding=(0, 2))
        t.add_column("Key", style="bold cyan", no_wrap=True)
        t.add_column("Value", style="white")

        status_text = Text("Online", style="bold green")
        status_text.stylize("green")
        tunnel_url = self.server_url.replace("{code}", self.tunnel.code)
        t.add_row("Session Status", "● Online")
        t.add_row("Tunnel URL", tunnel_url)
        t.add_row("Local Target", f"http://localhost:{self.tunnel.local_port}")
        lat_ms = self.tunnel.latency
        lat_str = f"{lat_ms:.0f}ms" if lat_ms > 0 else "N/A"
        t.add_row("Latency", lat_str)
        t.add_row("Requests", str(self.tunnel.request_count))
        return t

    def _build_log_panel(self) -> Panel:
        if not self.logs:
            return Panel("Waiting for activity...", title="Logs", border_style="dim")
        recent = "\n".join(self.logs[-15:])
        return Panel(recent, title="Logs", border_style="dim")

    def _build_layout(self) -> Layout:
        layout = Layout()
        layout.split_column(
            Layout(name="status", size=12),
            Layout(name="logs"),
        )
        layout["status"].update(
            Panel(self._build_status_table(), title=f"Tunnel: {self.tunnel.code}",
                  border_style="green", box=box.ROUNDED)
        )
        layout["logs"].update(self._build_log_panel())
        return layout

    async def refresh_loop(self):
        try:
            with Live(self._build_layout(), console=self.console,
                      refresh_per_second=2, screen=True) as live:
                self._live = live
                while True:
                    live.update(self._build_layout())
                    await asyncio.sleep(0.5)
        except (asyncio.CancelledError, KeyboardInterrupt):
            pass
        finally:
            self._live = None

    def stop(self):
        pass
