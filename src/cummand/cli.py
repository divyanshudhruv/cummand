"""CLI layer — defines all typer commands and orchestration."""

from cummand.tunnel import TunnelSession
import asyncio
import logging
import os
import urllib.parse
import webbrowser
from typing import Optional

import typer
from rich.console import Console
from rich.table import Table

from cummand import __version__
from cummand.config import (
    read_config,
    add_alias,
    remove_alias,
    set_option,
    init_config,
    CummandConfig,
    CONFIG_FILENAME,
    GLOBAL_CONFIG_DIR,
)
from cummand.client import run_tunnel
from cummand.server import run_server
from cummand.dashboard import Dashboard

app = typer.Typer(
    help="cummand - expose local servers to the internet",
)
config_app = typer.Typer(help="Manage configuration aliases and defaults")
app.add_typer(config_app, name="config")

console = Console()
logger = logging.getLogger(__name__)


def _version_callback(value: bool) -> None:
    if value:
        console.print(f"cummand v{__version__}")
        raise typer.Exit()


@app.callback(invoke_without_command=True)
def _main_callback(
    ctx: typer.Context,
    version: bool = typer.Option(
        False, "--version", "-V", help="Show version and exit",
        callback=_version_callback, is_eager=True),
):
    if ctx.invoked_subcommand is None and not version:
        console.print(ctx.get_help())
        raise typer.Exit()


def setup_logging(level: str = "info") -> None:
    logging.basicConfig(
        level=logging.DEBUG if level == "debug" else logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
        datefmt="%H:%M:%S",
    )


# ── Core commands ──


@app.command()
def tunnel(
    url: Optional[str] = typer.Argument(
        None, help="Local URL to tunnel (e.g. http://localhost:3000)"),
    alias: Optional[str] = typer.Option(
        None, "--alias", "-a", help="Use a saved alias profile"),
    server_url: Optional[str] = typer.Option(
        None, "--server", "-s", help="Relay server URL (overrides config)"),
    auth_token: Optional[str] = typer.Option(
        os.environ.get("CUMMAND_AUTH_TOKEN", None), "--auth-token", help="Auth token for relay server"),
    log_level: Optional[str] = typer.Option(
        None, "--log-level", "-l", help="Log level: debug | info"),
    retry_limit: Optional[int] = typer.Option(
        None, "--retry-limit", "-r", help="Max reconnection attempts"),
    global_: bool = typer.Option(
        False, "--global", "-g", help="Use global config (~/.cummand/)"),
):
    """Start a tunnel to expose a local server to the internet."""
    cfg = read_config(global_=global_)

    if auth_token:
        cfg.auth.token = auth_token

    tunnel_url: str = ""

    if alias:
        if alias not in cfg.aliases:
            console.print(f"[red]Alias '{alias}' not found in config.[/red]")
            console.print("Add it: cummand config add --alias <name> --url <url>")
            raise typer.Exit(1)
        alias_cfg = cfg.aliases[alias]
        tunnel_url = alias_cfg.url
    elif url:
        tunnel_url = url
    else:
        console.print("[red]Provide a URL to tunnel or use --alias <name> to use a saved profile.[/red]")
        console.print("Usage: cummand tunnel http://localhost:3000")
        console.print("       cummand tunnel --alias frontend")
        raise typer.Exit(1)

    local_port = _parse_port(tunnel_url)

    level = log_level or cfg.defaults.log_level
    setup_logging(level)

    resolved_server_url = server_url or cfg.defaults.server_url
    retries = retry_limit or cfg.defaults.retry_limit

    cfg.defaults.retry_limit = retries
    cfg.defaults.log_level = level

    _run_client(cfg, local_port, resolved_server_url)


def _run_client(cfg: CummandConfig, local_port: int, server_url: str) -> None:
    """Run the tunnel client with a live dashboard."""
    dashboard: Optional[Dashboard] = None
    tunnel_session = None
    tunnel_ready = asyncio.Event()

    def on_code(code: str) -> None:
        tunnel_url_public = cfg.defaults.public_url.replace("{code}", code)
        if cfg.defaults.auto_open:
            webbrowser.open(tunnel_url_public)
            console.print(
                f"[green]Opening {tunnel_url_public} in browser...[/green]")

    def on_log(msg: str) -> None:
        console.print(f"[dim]{msg}[/dim]")

    def on_tunnel_ready(tunnel: TunnelSession) -> None:
        nonlocal tunnel_session
        tunnel_session = tunnel
        tunnel_ready.set()

    async def entry():
        nonlocal dashboard, tunnel_session

        async def run_with_dashboard():
            await run_tunnel(
                server_url=server_url,
                local_port=local_port,
                config=cfg,
                on_code=on_code,
                on_log=on_log,
                on_tunnel_ready=on_tunnel_ready,
                auth_token=cfg.auth.token,
            )

        tunnel_task = asyncio.create_task(run_with_dashboard())

        await tunnel_ready.wait()

        dashboard = Dashboard(tunnel_session, cfg.defaults.public_url)
        dashboard_task = asyncio.create_task(dashboard.refresh_loop())

        try:
            await tunnel_task
        except Exception as e:
            console.print(f"[red]Tunnel error: {e}[/red]")
            raise typer.Exit(1)
        finally:
            dashboard_task.cancel()

    try:
        asyncio.run(entry())
    except KeyboardInterrupt:
        console.print(
            "\n[black on red bold] TUNNEL CLOSED [/black on red bold]")


@app.command()
def serve(
    port: int = typer.Option(
        int(os.environ.get("PORT", "8080")), "--port", "-p", help="Port to listen on"),
    auth_token: str = typer.Option(
        os.environ.get("CUMMAND_AUTH_TOKEN", ""), "--auth-token", help="Require auth token from clients"),
    tunnel: Optional[str] = typer.Option(
        None, "--tunnel", "-t", help="Also tunnel this local URL in the same process"),
    log_level: str = typer.Option("info", "--log-level", "-l", help="Log level: debug | info"),
):
    """Start the relay server (optionally with a tunnel client)."""
    setup_logging(log_level)

    if tunnel:
        console.print(f"[green]Starting server on :{port} with tunnel to {tunnel}...[/green]")
        if auth_token:
            console.print("[yellow]Auth token required for clients.[/yellow]")

        local_port = _parse_port(tunnel)
        server_url = f"ws://localhost:{port}"

        async def entry():
            cfg = CummandConfig()
            cfg.defaults.server_url = server_url
            cfg.defaults.public_url = f"http://localhost:{port}/{{code}}"
            cfg.auth.token = auth_token

            async def client():
                await run_tunnel(
                    server_url=server_url,
                    local_port=local_port,
                    config=cfg,
                    on_log=lambda msg: console.print(f"[dim]{msg}[/dim]"),
                    auth_token=auth_token,
                )

            await asyncio.gather(run_server(port, auth_token), client())

        try:
            asyncio.run(entry())
        except KeyboardInterrupt:
            console.print("\n[yellow]Server stopped.[/yellow]")
        return

    console.print(f"[green]Starting server on :{port} (HTTP + WebSocket)...[/green]")
    if auth_token:
        console.print("[yellow]Auth token required for clients.[/yellow]")

    try:
        asyncio.run(run_server(port, auth_token))
    except KeyboardInterrupt:
        console.print("\n[yellow]Server stopped.[/yellow]")


def _parse_port(url: str) -> int:
    """Extract the port number from a URL or bare port string."""
    if "://" in url:
        parsed = urllib.parse.urlparse(url)
        return parsed.port or {"http": 80, "https": 443}.get(parsed.scheme, 3000)
    try:
        return int(url.strip("/"))
    except ValueError:
        console.print(f"[red]Invalid URL: {url}[/red]")
        raise typer.Exit(1)


# ── Config commands ──


@config_app.command("init")
def config_init(
    global_: bool = typer.Option(
        False, "--global", "-g", help=f"Install in ~/{GLOBAL_CONFIG_DIR}/ for global use"),
):
    """Create a default cummand.config.toml."""
    path = init_config(global_=global_)
    console.print(f"[green]Default config created at: {path}[/green]")
    if global_:
        console.print(
            "[dim]This config will be used as fallback when no local config exists.[/dim]")


@config_app.command("list")
def config_list(
    global_: bool = typer.Option(
        False, "--global", "-g", help="Use global config (~/.cummand/)"),
):
    """List all configured aliases."""
    cfg = read_config(global_=global_)
    if not cfg.aliases:
        console.print("[yellow]No aliases configured.[/yellow]")
        console.print("Add one: cummand config add --alias <name> --url <url>")
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
    global_: bool = typer.Option(
        False, "--global", "-g", help="Use global config (~/.cummand/)"),
):
    """Add a new alias profile."""
    add_alias(alias_name, url, description, global_=global_)
    console.print(f"[green]Alias '{alias_name}' added.[/green]")


@config_app.command("remove")
def config_remove(
    alias_name: str = typer.Option(..., "--alias", "-a", help="Alias name"),
    global_: bool = typer.Option(
        False, "--global", "-g", help="Use global config (~/.cummand/)"),
):
    """Remove an alias profile."""
    remove_alias(alias_name, global_=global_)
    console.print(f"[green]Alias '{alias_name}' removed.[/green]")


@config_app.command("set")
def config_set(
    key: str = typer.Argument(..., help="Config key: auth-token | server-url | public-url | log-level | auto-open | retry-limit"),
    value: str = typer.Argument(..., help="Config value"),
    global_: bool = typer.Option(
        False, "--global", "-g", help="Use global config (~/.cummand/)"),
):
    """Set a single config option.

    Examples:
      cummand config set log-level debug
      cummand config set server-url wss://relay.example.com
      cummand config set auto-open false
      cummand config set retry-limit 10
    """
    key = key.replace("_", "-")
    known = {"auth-token", "log-level", "auto-open", "retry-limit", "server-url", "public-url"}
    if key not in known:
        console.print(f"[red]Unknown key: {key}. Allowed: {', '.join(sorted(known))}[/red]")
        raise typer.Exit(1)

    try:
        set_option(key, value, global_=global_)
        console.print(f"[green]{key} set to: {value}[/green]")
    except ValueError as e:
        console.print(f"[red]{e}[/red]")


def main():
    app()
