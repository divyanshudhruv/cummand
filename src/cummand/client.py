"""Tunnel client — connects to relay server and proxies HTTP requests."""

import asyncio
import logging
import time
from collections.abc import Callable
from typing import Optional

import aiohttp
import websockets

from cummand.config import CummandConfig
from cummand.tunnel import MAX_MSG_SIZE, TunnelSession

logger = logging.getLogger(__name__)


async def fetch_and_relay(
    ws: websockets.ClientConnection,
    session: aiohttp.ClientSession,
    local_port: int,
    tunnel: TunnelSession,
    msg: bytes,
) -> None:
    """Receive a relayed HTTP request from the server, proxy it locally, and send back the response."""
    req_id = "unknown"
    path = "unknown"
    try:
        header_part, request_body = msg.split(b"|||", 1)
        req_id, method, path = header_part.decode().split(" ", 2)
        url = f"http://localhost:{local_port}{path}"
        start = time.monotonic()
        async with session.request(method, url, data=request_body or None) as resp:
            data = await resp.read()
            elapsed = time.monotonic() - start
            ctype = resp.headers.get(
                "Content-Type", "application/octet-stream")
            status = str(resp.status).encode()
            await ws.send(req_id.encode() + b"|||" + status + b"|||" + ctype.encode() + b"|||" + data)
            tunnel.request_count += 1
            tunnel.bytes_sent += len(data)
            tunnel.latency = elapsed * 1000
    except Exception as e:
        logger.debug("Relay error on %s: %s", path, e)
        if req_id != "unknown":
            try:
                zero = b"0"
                await ws.send(req_id.encode() + b"|||" + zero + b"|||" + b"ERROR" + b"|||" + str(e).encode())
            except Exception:
                pass


async def relay_loop(
    ws: websockets.ClientConnection,
    local_port: int,
    tunnel: TunnelSession,
    session: aiohttp.ClientSession,
) -> None:
    """Listen for incoming messages from the server and dispatch each as a relay task."""
    while True:
        try:
            msg = await ws.recv()
            asyncio.create_task(fetch_and_relay(
                ws, session, local_port, tunnel, msg))
        except websockets.ConnectionClosed:
            break
        except Exception:
            break


async def run_tunnel(
    server_url: str,
    local_port: int,
    config: CummandConfig,
    on_code: Optional[Callable[[str], None]] = None,
    on_log: Optional[Callable[[str], None]] = None,
    on_tunnel_ready: Optional[Callable[[TunnelSession], None]] = None,
    auth_token: str = "",
) -> None:
    """Connect to the relay server, authenticate, and enter the relay loop."""
    retries = config.defaults.retry_limit
    attempt = 0

    token = auth_token or config.auth.token

    while attempt < retries:
        attempt += 1
        try:
            async with websockets.connect(
                server_url, max_size=MAX_MSG_SIZE
            ) as ws:
                code = (await ws.recv()).decode()
                if on_code:
                    on_code(code)

                if token:
                    await ws.send(token.encode())
                    auth_resp = (await ws.recv()).decode()
                    if auth_resp != "OK":
                        raise ConnectionError(f"Auth failed: {auth_resp}")

                if on_log:
                    on_log(f"Tunnel established — code: {code}")

                tunnel = TunnelSession(
                    code=code,
                    local_port=local_port,
                    ws=ws,
                    log_level=config.defaults.log_level,
                )

                if on_tunnel_ready:
                    on_tunnel_ready(tunnel)

                async with aiohttp.ClientSession() as session:
                    await relay_loop(ws, local_port, tunnel, session)
                break
        except (websockets.ConnectionClosed, ConnectionError, OSError) as e:
            logger.warning("Connection attempt %d/%d failed: %s",
                           attempt, retries, e)
            if on_log:
                on_log(f"Reconnecting ({attempt}/{retries})...")
            if attempt < retries:
                await asyncio.sleep(min(2 ** attempt, 30))
            else:
                if on_log:
                    on_log("Max retries reached. Giving up.")
                raise


if __name__ == "__main__":
    import sys
    from pathlib import Path

    # allow running from src/cummand/ without package install
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

    from cummand.cli import app
    app(["start"] + sys.argv[1:])
