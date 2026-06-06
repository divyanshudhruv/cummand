"""Relay server — accepts HTTP and WebSocket connections on a single port."""

import asyncio
import logging
import secrets
import uuid
import sys

from aiohttp import web

from cummand.generator import generate_code
from cummand.tunnel import MAX_MSG_SIZE, TunnelSession

logger = logging.getLogger(__name__)

# Workaround for Windows asyncio + aiohttp issue:
# _ProactorBasePipeTransport._call_connection_lost is called unexpectedly
# when a WebSocket is closed during cleanup on Windows.
# TODO: revisit when upstream bug is resolved
if sys.platform == "win32":
    from asyncio.proactor_events import _ProactorBasePipeTransport
    _ProactorBasePipeTransport._call_connection_lost = lambda self, *args: None

tunnels: dict[str, TunnelSession] = {}
server_auth_token: str = ""

LOCALHOST_SUFFIXES = {"localhost", "127.0.0.1", "::1", "0.0.0.0"}


def _extract_code_and_path(request: web.Request) -> tuple[str, str]:
    """Extract the tunnel code and remaining path from a host header or URL path."""
    host = request.host
    path = request.path

    if host:
        host_no_port = host.split(":")[0]
        dot_idx = host_no_port.find(".")
        if dot_idx > 0:
            potential_suffix = host_no_port[dot_idx + 1:]
            if potential_suffix in LOCALHOST_SUFFIXES:
                code = host_no_port[:dot_idx]
                return code, path

    p = path.lstrip("/")
    parts = p.split("/", 1)
    code = parts[0]
    remaining = ""
    if len(parts) > 1:
        remaining = "/" + parts[1]
    return code, remaining


async def handle_http(request: web.Request) -> web.Response:
    """Route an HTTP request to the correct tunnel and relay the response."""
    code, remaining = _extract_code_and_path(request)

    tunnel = tunnels.get(code)
    if not tunnel:
        referer = request.headers.get("Referer", "")
        if referer:
            for code_candidate in tunnels:
                if code_candidate in referer:
                    tunnel = tunnels[code_candidate]
                    remaining = request.path
                    break
        if not tunnel and len(tunnels) == 1:
            tunnel = next(iter(tunnels.values()))
            remaining = request.path
    if not tunnel:
        return web.Response(text=f"Tunnel '{code}' not found. Is the tunnel active?", status=404)

    req_body = await request.read()

    req_id = str(uuid.uuid4())
    future: asyncio.Future = asyncio.Future()
    tunnel.pending[req_id] = future
    tunnel.record_request()

    try:
        msg = f"{req_id} {request.method} {remaining}|||".encode() + req_body
        await tunnel.ws.send_bytes(msg)
        raw_payload = await asyncio.wait_for(future, timeout=30.0)
        status_code, header, body = raw_payload

        if header == b"ERROR":
            err_msg = body.decode("utf-8")
            return web.Response(text=f"Proxy error: {err_msg}", status=502)

        content_type = header.decode("utf-8").split(";")[0].strip()
        return web.Response(body=body, content_type=content_type, status=status_code)
    except asyncio.TimeoutError:
        return web.Response(text=f"Request timed out after 30s: {request.method} {remaining}", status=504)
    except Exception as e:
        return web.Response(text=f"Proxy error: {str(e)}", status=502)
    finally:
        tunnel.pending.pop(req_id, None)


async def ws_handler(request: web.Request) -> web.WebSocketResponse:
    """Accept a WebSocket connection, assign a tunnel code, and relay messages."""
    ws = web.WebSocketResponse(max_msg_size=MAX_MSG_SIZE)
    await ws.prepare(request)

    code = generate_code()
    while code in tunnels:
        code = generate_code()

    await ws.send_bytes(code.encode())

    try:
        msg = await asyncio.wait_for(ws.receive(), timeout=5.0)
        if msg.type in (web.WSMsgType.TEXT, web.WSMsgType.BINARY):
            token = msg.data
            if isinstance(token, bytes):
                token = token.decode()
            if server_auth_token and not secrets.compare_digest(token, server_auth_token):
                logger.warning("Auth rejected for %s: invalid token", code)
                await ws.send_bytes(b"ERROR: invalid token")
                return ws
            await ws.send_bytes(b"OK")
    except asyncio.TimeoutError:
        if server_auth_token:
            logger.warning("Auth timeout for %s: no token received", code)
            await ws.close()
            return ws
    except ConnectionResetError:
        return ws

    tunnel = TunnelSession(code=code, local_port=0, ws=ws)
    tunnels[code] = tunnel
    logger.info("Tunnel active: %s", code)

    try:
        async for msg in ws:
            if msg.type == web.WSMsgType.BINARY:
                raw = msg.data
                parts = raw.split(b"|||", 3)
                if len(parts) == 4:
                    req_id_bytes, status_bytes, header, body = parts
                    req_id = req_id_bytes.decode("utf-8")
                    status_code = int(status_bytes.decode("utf-8"))
                    if req_id in tunnel.pending:
                        if not tunnel.pending[req_id].done():
                            tunnel.pending[req_id].set_result((status_code, header, body))
            elif msg.type == web.WSMsgType.ERROR:
                break
    finally:
        tunnels.pop(code, None)
        logger.info("Tunnel disconnected: %s", code)
        for fut in tunnel.pending.values():
            if not fut.done():
                fut.set_exception(Exception("Tunnel disconnected"))

    return ws


async def root_handler(request: web.Request) -> web.WebSocketResponse | web.Response:
    """Route incoming requests: WebSocket upgrades to ws_handler, others to handle_http."""
    if request.headers.get("Upgrade", "").lower() == "websocket":
        return await ws_handler(request)
    return await handle_http(request)


async def health(request: web.Request) -> web.Response:
    """Health check endpoint returning tunnel count."""
    return web.Response(text=f"cummand server {len(tunnels)} tunnels", status=200)


async def run_server(port: int = 8080, auth_token: str = "") -> None:
    """Start the aiohttp relay server on the given port."""
    global server_auth_token
    server_auth_token = auth_token

    logging.getLogger("aiohttp.access").setLevel(logging.WARNING)

    app = web.Application()
    app.router.add_get("/health", health)
    app.router.add_route("*", "/", root_handler)
    app.router.add_route("*", "/{tail:.*}", root_handler)
    runner = web.AppRunner(app)
    await runner.setup()
    await web.TCPSite(runner, "0.0.0.0", port).start()

    logger.info("Server listening on :%d (HTTP + WebSocket)", port)

    await asyncio.Future()


if __name__ == "__main__":
    import os
    port = int(os.environ.get("PORT", 8080))
    auth = os.environ.get("CUMMAND_AUTH_TOKEN", "")
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s", datefmt="%H:%M:%S")
    asyncio.run(run_server(port, auth))
