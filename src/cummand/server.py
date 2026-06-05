import asyncio
import logging
import uuid
import sys

from aiohttp import web

from cummand.generator import generate_code
from cummand.tunnel import TunnelSession

logger = logging.getLogger(__name__)

if sys.platform == "win32":
    from asyncio.proactor_events import _ProactorBasePipeTransport
    _ProactorBasePipeTransport._call_connection_lost = lambda self, *args: None

tunnels: dict[str, TunnelSession] = {}
server_auth_token: str = ""

LOCALHOST_SUFFIXES = {"localhost", "127.0.0.1", "::1", "0.0.0.0"}


def _extract_code_and_path(request: web.Request) -> tuple[str | None, str]:
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
    code, remaining = _extract_code_and_path(request)

    tunnel = tunnels.get(code)
    if not tunnel:
        return web.Response(text="Tunnel not found", status=404)

    req_body = await request.read()

    req_id = str(uuid.uuid4())
    fut: asyncio.Future = asyncio.Future()
    tunnel.pending[req_id] = fut
    tunnel.record_request()

    try:
        msg = f"{req_id} {request.method} {remaining}|||".encode() + req_body
        await tunnel.ws.send_bytes(msg)
        raw_payload = await asyncio.wait_for(fut, timeout=30.0)
        status_code, header, body = raw_payload

        if header == b"ERROR":
            return web.Response(text=f"Proxy Error: {body.decode('utf-8')}", status=502)

        ctype = header.decode("utf-8").split(";")[0].strip()
        return web.Response(body=body, content_type=ctype, status=status_code)
    except asyncio.TimeoutError:
        return web.Response(text="Proxy Timeout", status=504)
    except Exception as e:
        return web.Response(text=f"Proxy Error: {str(e)}", status=502)
    finally:
        tunnel.pending.pop(req_id, None)


async def ws_handler(request: web.Request) -> web.WebSocketResponse:
    ws = web.WebSocketResponse(max_msg_size=20 * 1024 * 1024)
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
            if server_auth_token and token != server_auth_token:
                await ws.send_bytes(b"ERROR: invalid token")
                return ws
            await ws.send_bytes(b"OK")
    except (asyncio.TimeoutError, ConnectionResetError):
        pass

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
        for fut in list(tunnel.pending.values()):
            if not fut.done():
                fut.set_exception(Exception("Tunnel disconnected"))

    return ws


async def root_handler(request: web.Request) -> web.WebSocketResponse | web.Response:
    if request.headers.get("Upgrade", "").lower() == "websocket":
        return await ws_handler(request)
    return await handle_http(request)


async def run_server(port: int = 8080, auth_token: str = "") -> None:
    global server_auth_token
    server_auth_token = auth_token

    app = web.Application()
    app.router.add_route("*", "/{tail:.*}", root_handler)
    runner = web.AppRunner(app)
    await runner.setup()
    await web.TCPSite(runner, "0.0.0.0", port).start()

    logger.info("Server listening on :%d (HTTP + WebSocket)", port)

    await asyncio.Future()
