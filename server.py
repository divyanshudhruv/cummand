import asyncio
import sys
import uuid
from aiohttp import web
import websockets

# Suppress Windows socket noise
if sys.platform == 'win32':
    from asyncio.proactor_events import _ProactorBasePipeTransport
    _ProactorBasePipeTransport._call_connection_lost = lambda self, *args: None

tunnels = {}


class Tunnel:
    def __init__(self, ws):
        self.ws = ws
        self.pending = {}


async def handle_http(request):
    tunnel = list(tunnels.values())[0] if tunnels else None
    if not tunnel:
        return web.Response(text="Tunnel not found", status=404)

    req_id = str(uuid.uuid4())
    fut = asyncio.Future()
    tunnel.pending[req_id] = fut

    try:
        await tunnel.ws.send(f"{req_id} {request.method} {request.path_qs}".encode())
        raw_payload = await asyncio.wait_for(fut, timeout=30.0)

        header, body = raw_payload

        if header == b"ERROR":
            return web.Response(text=f"Proxy Error: {body.decode('utf-8')}", status=502)

        ctype = header.decode('utf-8').split(';')[0].strip()

        return web.Response(body=body, content_type=ctype)
    except asyncio.TimeoutError:
        return web.Response(text="Proxy Timeout", status=504)
    except Exception as e:
        return web.Response(text=f"Proxy Error: {str(e)}", status=502)
    finally:
        tunnel.pending.pop(req_id, None)


async def ws_handler(ws):
    subdomain = (await ws.recv()).decode()
    tunnel = Tunnel(ws)
    tunnels[subdomain] = tunnel
    print(f"✅ Tunnel active: {subdomain}")
    try:
        while True:
            try:
                raw_payload = await ws.recv()
                parts = raw_payload.split(b"|||", 2)
                if len(parts) == 3:
                    req_id_bytes, header, body = parts
                    req_id = req_id_bytes.decode('utf-8')
                    if req_id in tunnel.pending:
                        if not tunnel.pending[req_id].done():
                            tunnel.pending[req_id].set_result((header, body))
            except websockets.ConnectionClosed:
                break
            except Exception as e:
                print(f"Error reading from tunnel: {e}")
                break
    finally:
        tunnels.pop(subdomain, None)

        # Cancel all pending requests
        for fut in list(tunnel.pending.values()):
            if not fut.done():
                fut.set_exception(Exception("Tunnel disconnected"))


async def main():
    app = web.Application()
    app.router.add_route('*', '/{tail:.*}', handle_http)
    runner = web.AppRunner(app)
    await runner.setup()
    await web.TCPSite(runner, '0.0.0.0', 8080).start()
    async with websockets.serve(ws_handler, "0.0.0.0", 8765, max_size=20*1024*1024):
        await asyncio.Future()

if __name__ == "__main__":
    asyncio.run(main())
