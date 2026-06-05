import asyncio
import tomllib
import websockets
import aiohttp

async def fetch_and_relay(ws, session, local_port, msg):
    req_id = "unknown"
    path = "unknown"
    try:
        req_id, method, path = msg.decode().split(" ", 2)
        url = f"http://localhost:{local_port}{path}"
        async with session.request(method, url, headers={"Host": f"localhost:{local_port}"}) as resp:
            data = await resp.read()
            ctype = resp.headers.get('Content-Type', 'application/octet-stream')
            # Send: [req_id] + ||| + [Header] + ||| + [Binary Body]
            await ws.send(req_id.encode() + b"|||" + ctype.encode() + b"|||" + data)
    except Exception as e:
        print(f"Relay error on {path}: {e}")
        if req_id != "unknown":
            try:
                await ws.send(req_id.encode() + b"|||" + b"ERROR" + b"|||" + str(e).encode())
            except Exception:
                pass

async def relay(ws, local_port):
    async with aiohttp.ClientSession() as session:
        while True:
            try:
                msg = await ws.recv()
                asyncio.create_task(fetch_and_relay(ws, session, local_port, msg))
            except Exception:
                break

def start(config="cummand.toml"):
    with open(config, "rb") as f:
        cfg = tomllib.load(f)
    
    async def run():
        url = cfg['tunnel']['server_url']
        sub = cfg['tunnel']['subdomain']
        port = cfg['tunnel']['local_port']
        async with websockets.connect(url, max_size=20*1024*1024) as ws:
            await ws.send(sub.encode())
            await relay(ws, port)

    asyncio.run(run())

if __name__ == "__main__":
    start()