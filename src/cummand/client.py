import asyncio
import logging
import time

import aiohttp
import websockets

from cummand.config import CummandConfig
from cummand.tunnel import TunnelSession
from cummand.generator import generate_code

logger = logging.getLogger(__name__)


async def fetch_and_relay(
    ws: websockets.WebSocketClientProtocol,
    session: aiohttp.ClientSession,
    local_port: int,
    tunnel: TunnelSession,
    msg: bytes,
) -> None:
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
    ws: websockets.WebSocketClientProtocol,
    local_port: int,
    tunnel: TunnelSession,
    session: aiohttp.ClientSession,
) -> None:
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
    on_code: callable = None,
    on_log: callable = None,
    on_tunnel_ready: callable = None,
) -> None:
    retries = config.defaults.retry_limit
    attempt = 0

    while attempt < retries:
        attempt += 1
        try:
            async with websockets.connect(
                server_url, max_size=20 * 1024 * 1024
            ) as ws:
                code = (await ws.recv()).decode()
                if on_code:
                    on_code(code)

                if config.auth.token:
                    await ws.send(config.auth.token.encode())
                    auth_resp = (await ws.recv()).decode()
                    if auth_resp != "OK":
                        raise ConnectionError(f"Auth failed: {auth_resp}")

                if on_log:
                    on_log(f"Tunnel established — code: {code}")
                    print("")

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
