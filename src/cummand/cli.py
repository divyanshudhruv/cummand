import asyncio
import logging
import webbrowser
from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.table import Table

from cummand.config import (
    read_config,
    write_config,
    add_alias,
    remove_alias,
    set_option,
    CummandConfig,
    CONFIG_FILENAME,
)
from cummand.client import run_tunnel
from cummand.server import run_server
from cummand.dashboard import Dashboard

app = typer.Typer(help="cummand — expose local servers to the internet")
config_app = typer.Typer(help="Manage configuration")
server_app = typer.Typer(help="Manage relay server")
app.add_typer(config_app, name="config")
app.add_typer(server_app, name="server")

console = Console()
logger = logging.getLogger(__name__)


def setup_logging(level: str = "info"):
    logging.basicConfig(
        level=logging.DEBUG if level == "debug" else logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
        datefmt="%H:%M:%S",
    )


@app.command()
def start(
    url: Optional[str] = typer.Argument(None, help="Local URL to tunnel (ad-hoc mode)"),
    alias: Optional[str] = typer.Option(None, "--alias", "-a", help="Profile alias from config"),
    server_url: Optional[str] = typer.Option(None, "--server", "-s", help="Relay server URL"),
    log_level: Optional[str] = typer.Option(None, "--log-level", "-l", help="Log level (debug|info)"),
    retry_limit: Optional[int] = typer.Option(None, "--retry-limit", "-r", help="Max reconnection attempts"),
):
    """Start a tunnel to expose a local server."""
    cfg = read_config()

    local_port: int = 0
    tunnel_url: str = ""

    if alias:
        if alias not in cfg.aliases:
            console.print(f"[red]Alias '{alias}' not found in config.[/red]")
            raise typer.Exit(1)
        alias_cfg = cfg.aliases[alias]
        tunnel_url = alias_cfg.url
    elif url:
        tunnel_url = url
    else:
        console.print("[red]Provide a URL or --alias.[/red]")
        console.print("Usage: cummand start http://localhost:3000")
        console.print("       cummand start --alias frontend")
        raise typer.Exit(1)

    if "://" in tunnel_url:
        import urllib.parse
        parsed = urllib.parse.urlparse(tunnel_url)
        local_port = parsed.port or {"http": 80, "https": 443}.get(parsed.scheme, 3000)
    else:
        try:
            local_port = int(tunnel_url.strip("/"))
        except ValueError:
            console.print(f"[red]Invalid URL: {tunnel_url}[/red]")
            raise typer.Exit(1)

    level = log_level or cfg.defaults.log_level
    setup_logging(level)

    srv = server_url or cfg.defaults.server_url
    retries = retry_limit or cfg.defaults.retry_limit

    cfg.defaults.retry_limit = retries
    cfg.defaults.log_level = level

    code_container: list[str] = []
    dashboard: Optional[Dashboard] = None

    def on_code(code: str):
        code_container.append(code)
        tunnel_url_public = cfg.defaults.public_url.replace("{code}", code)
        if cfg.defaults.auto_open:
            webbrowser.open(tunnel_url_public)
            console.print(f"[green]Opening {tunnel_url_public} in browser...[/green]")

    def on_log(msg: str):
        if dashboard:
            dashboard.log(msg)
        else:
            console.print(f"[dim]{msg}[/dim]")

    async def entry():
        nonlocal dashboard
        tunnel = None
        try:
            await run_tunnel(
                server_url=srv,
                local_port=local_port,
                config=cfg,
                on_code=on_code,
                on_log=on_log,
            )

            if code_container:
                tunnel = type("Tunnel", (), {
                    "code": code_container[0],
                    "local_port": local_port,
                    "latency": 0.0,
                    "request_count": 0,
                    "log_level": level,
                })()
                dashboard = Dashboard(tunnel, cfg.defaults.public_url)
                await dashboard.refresh_loop()
        except Exception as e:
            console.print(f"[red]Error: {e}[/red]")
            raise typer.Exit(1)

    try:
        asyncio.run(entry())
    except KeyboardInterrupt:
        console.print("\n[yellow]Tunnel closed.[/yellow]")


@config_app.command("list")
def config_list():
    """List all configured aliases."""
    cfg = read_config()
    if not cfg.aliases:
        console.print("[yellow]No aliases configured.[/yellow]")
        console.print(f"Add one: cummand config add --alias <name> --url <url>")
        return

    table = Table(title="Configured Aliases")
    table.add_column("Alias", style="cyan", no_wrap=True)
    table.add_column("URL", style="green")
    table.add_column("Description", style="white")

    for name, alias_cfg in cfg.aliases.items():
        table.add_row(name, alias_cfg.url, alias_cfg.description or "—")

    console.print(table)


@config_app.command("add")
def config_add(
    alias_name: str = typer.Option(..., "--alias", "-a", help="Alias name"),
    url: str = typer.Option(..., "--url", "-u", help="Local URL to tunnel"),
    description: str = typer.Option("", "--desc", "-d", help="Description"),
):
    """Add a new alias profile."""
    add_alias(alias_name, url, description)
    console.print(f"[green]Alias '{alias_name}' added.[/green]")


@config_app.command("remove")
def config_remove(
    alias_name: str = typer.Option(..., "--alias", "-a", help="Alias name"),
):
    """Remove an alias profile."""
    remove_alias(alias_name)
    console.print(f"[green]Alias '{alias_name}' removed.[/green]")


@config_app.command("set")
def config_set(
    auth_token: Optional[str] = typer.Option(None, "--auth-token", help="Set auth token"),
    log_level: Optional[str] = typer.Option(None, "--log-level", help="Set log level (debug|info)"),
    auto_open: Optional[str] = typer.Option(None, "--auto-open", help="Auto-open browser (true|false)"),
    retry_limit: Optional[int] = typer.Option(None, "--retry-limit", help="Set retry limit"),
    server_url: Optional[str] = typer.Option(None, "--server", help="Set relay server URL"),
    public_url: Optional[str] = typer.Option(None, "--public-url", help="Set public-facing URL (e.g. http://localhost:8080)"),
):
    """Set configuration options."""
    set_count = 0
    pairs = [
        ("auth-token", auth_token),
        ("log-level", log_level),
        ("auto-open", auto_open),
        ("retry-limit", str(retry_limit) if retry_limit is not None else None),
    ]

    if server_url:
        try:
            cfg = read_config()
            cfg.defaults.server_url = server_url
            write_config(cfg)
            console.print(f"[green]server_url set to: {server_url}[/green]")
            set_count += 1
        except Exception as e:
            console.print(f"[red]Error: {e}[/red]")

    if public_url:
        try:
            cfg = read_config()
            cfg.defaults.public_url = public_url
            write_config(cfg)
            console.print(f"[green]public_url set to: {public_url}[/green]")
            set_count += 1
        except Exception as e:
            console.print(f"[red]Error: {e}[/red]")

    for key, value in pairs:
        if value is not None:
            try:
                set_option(key, value)
                console.print(f"[green]{key} set to: {value}[/green]")
                set_count += 1
            except ValueError as e:
                console.print(f"[red]{e}[/red]")

    if set_count == 0:
        console.print("[yellow]No options provided. Use --help to see available options.[/yellow]")


@server_app.command("start")
def server_start(
    port: int = typer.Option(8080, "--port", "-p", help="Port to listen on"),
    auth_token: str = typer.Option("", "--auth-token", help="Required client auth token"),
    log_level: str = typer.Option("info", "--log-level", "-l", help="Log level"),
):
    """Start the relay server."""
    setup_logging(log_level)
    console.print(f"[green]Starting server on :{port} (HTTP + WebSocket)...[/green]")
    if auth_token:
        console.print("[yellow]Auth token required for clients.[/yellow]")

    try:
        asyncio.run(run_server(port, auth_token))
    except KeyboardInterrupt:
        console.print("\n[yellow]Server stopped.[/yellow]")


def main():
    app()
