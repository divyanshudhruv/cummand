"""Relay server — accepts HTTP and WebSocket connections on a single port."""

import asyncio
import logging
import os
import secrets
import time
import uuid
import sys
from collections import defaultdict
from datetime import datetime, timezone

from aiohttp import web

from cummand import __version__
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

# Rate limiting — tracks connection timestamps per IP
_connection_counts: dict[str, list[float]] = defaultdict(list)
MAX_TUNNELS = int(os.environ.get("CUMMAND_MAX_TUNNELS", "500"))
RATE_LIMIT = int(os.environ.get("CUMMAND_RATE_LIMIT", "5"))
RATE_WINDOW = int(os.environ.get("CUMMAND_RATE_WINDOW", "60"))

# Stats database
db_pool = None
ADMIN_TOKEN = os.environ.get("CUMMAND_ADMIN_TOKEN", "")

LOCALHOST_SUFFIXES = {"localhost", "127.0.0.1", "::1", "0.0.0.0"}


async def _get_db_pool():
    global db_pool
    if db_pool is None:
        dsn = os.environ.get("CUMMAND_DATABASE_URL", "")
        if dsn:
            import asyncpg
            db_pool = await asyncpg.create_pool(dsn, min_size=1, max_size=5)
    return db_pool


async def _ensure_stats_table(pool):
    await pool.execute("""
        CREATE TABLE IF NOT EXISTS tunnel_history (
            id          SERIAL PRIMARY KEY,
            code        VARCHAR(100) NOT NULL,
            started_at  TIMESTAMPTZ NOT NULL,
            ended_at    TIMESTAMPTZ NOT NULL,
            duration_s  INT NOT NULL,
            requests    INT NOT NULL,
            bytes_sent  BIGINT NOT NULL,
            latency_ms  FLOAT DEFAULT 0
        )
    """)


def _check_admin(request) -> web.Response | None:
    if not ADMIN_TOKEN:
        return web.Response(text="Admin API not configured", status=401)
    auth = request.headers.get("Authorization", "")
    if not auth.startswith("Bearer ") or auth[7:] != ADMIN_TOKEN:
        return web.Response(text="Unauthorized", status=401)
    return None


async def handle_stats(request: web.Request) -> web.Response:
    err = _check_admin(request)
    if err:
        return err

    active = []
    for code, tunnel in tunnels.items():
        active.append({
            "code": code,
            "uptime_s": int(tunnel.uptime),
            "requests": tunnel.request_count,
            "bytes_sent": tunnel.bytes_sent,
            "latency_ms": tunnel.latency,
        })

    summary = {
        "active_count": len(active),
        "historical_count": 0,
        "total_requests_all_time": 0,
        "total_bytes_all_time": 0,
    }

    pool = await _get_db_pool()
    if pool:
        try:
            row = await pool.fetchrow(
                "SELECT COUNT(*)::int AS cnt, COALESCE(SUM(requests), 0)::bigint AS reqs, COALESCE(SUM(bytes_sent), 0)::bigint AS bytes FROM tunnel_history"
            )
            if row:
                summary["historical_count"] = row["cnt"]
                summary["total_requests_all_time"] = row["reqs"]
                summary["total_bytes_all_time"] = row["bytes"]
        except Exception as e:
            logger.warning("Stats DB query failed: %s", e)

    return web.json_response({"active": active, "summary": summary})


async def handle_history(request: web.Request) -> web.Response:
    err = _check_admin(request)
    if err:
        return err

    pool = await _get_db_pool()
    if not pool:
        return web.json_response({"error": "Database not configured"}, status=503)

    limit = int(request.query.get("limit", "50"))
    offset = int(request.query.get("offset", "0"))

    try:
        rows = await pool.fetch(
            "SELECT * FROM tunnel_history ORDER BY ended_at DESC LIMIT $1 OFFSET $2",
            limit, offset,
        )
        records = []
        for row in rows:
            records.append({
                "id": row["id"],
                "code": row["code"],
                "started_at": row["started_at"].isoformat(),
                "ended_at": row["ended_at"].isoformat(),
                "duration_s": row["duration_s"],
                "requests": row["requests"],
                "bytes_sent": row["bytes_sent"],
                "latency_ms": row["latency_ms"],
            })
        return web.json_response({"records": records, "limit": limit, "offset": offset})
    except Exception as e:
        return web.json_response({"error": str(e)}, status=500)


def _rate_limited(ip: str) -> bool:
    """Check if an IP has exceeded the connection rate limit."""
    now = time.time()
    cutoff = now - RATE_WINDOW
    timestamps = [t for t in _connection_counts[ip] if t > cutoff]
    _connection_counts[ip] = timestamps
    if len(timestamps) >= RATE_LIMIT:
        return True
    _connection_counts[ip].append(now)
    return False


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
    if len(tunnels) >= MAX_TUNNELS:
        return web.Response(text="Server full", status=503)

    peer = request.remote
    if peer and _rate_limited(peer):
        logger.warning("Rate limit exceeded for %s", peer)
        return web.Response(text="Too many connections", status=429)

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

        pool = await _get_db_pool()
        if pool:
            try:
                ended_at = datetime.now(timezone.utc)
                started_at = datetime.fromtimestamp(tunnel.start_time, tz=timezone.utc)
                duration = int(time.time() - tunnel.start_time)
                await pool.execute(
                    "INSERT INTO tunnel_history (code, started_at, ended_at, duration_s, requests, bytes_sent, latency_ms) VALUES ($1, $2, $3, $4, $5, $6, $7)",
                    code, started_at, ended_at, duration, tunnel.request_count, tunnel.bytes_sent, tunnel.latency,
                )
            except Exception as e:
                logger.warning("Failed to record tunnel history: %s", e)

    return ws


async def root_handler(request: web.Request) -> web.WebSocketResponse | web.Response:
    """Route incoming requests: WebSocket upgrades to ws_handler, others to handle_http."""
    if request.headers.get("Upgrade", "").lower() == "websocket":
        return await ws_handler(request)

    path = request.path
    if path == "/stats":
        return await handle_stats(request)
    if path == "/stats/history":
        return await handle_history(request)

    return await handle_http(request)


async def health(request: web.Request) -> web.Response:
    """Health check returning JSON with server status and version."""
    return web.json_response({
        "status": "ok",
        "version": __version__,
        "tunnels": len(tunnels),
    })


async def run_server(port: int = 8080, auth_token: str = "") -> None:
    """Start the aiohttp relay server on the given port."""
    global server_auth_token
    server_auth_token = auth_token

    logging.getLogger("aiohttp.access").setLevel(logging.WARNING)

    pool = await _get_db_pool()
    if pool:
        try:
            await _ensure_stats_table(pool)
            logger.info("Database connected, stats table ready")
        except Exception as e:
            logger.warning("Database init failed (stats disabled): %s", e)
            global db_pool
            await pool.close()
            db_pool = None
    else:
        logger.info("No CUMMAND_DATABASE_URL set — history stats disabled")

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
