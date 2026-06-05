# Cummand Documentation

- [CLI Reference](cli.md) — all commands and options
- [Configuration](configuration.md) — config file reference
- [Contributing](../CONTRIBUTING.md) — development guide

## Installation

### Usage (production)
```bash
bash scripts/install.sh
```

### Development
```bash
make dev
# or: pip install -e .
```

---

## Overview

`cummand` is an open-source ngrok alternative. It works in two parts:

1. **Server** — a public relay server that accepts HTTP connections and forwards them through WebSocket tunnels
2. **Client** — runs on your dev machine, connects to the server, and relays requests to your local server

## Quick Start

Choose the mode that fits your workflow:

### Single-Terminal Mode (local development, recommended)

Runs the relay server and tunnel client **in one process**. Your local app is tunneled automatically.

```bash
cummand serve --tunnel http://localhost:3000
```

That's it — one command, one terminal. The server listens on `:8080` and the client connects to it immediately.

### Two-Terminal Mode (self-hosting)

Server and client run in separate terminals. Use this when you want to keep the server running while restarting the client, or when they're on different machines.

```bash
# Terminal 1: start the relay server
cummand serve

# Terminal 2: start the tunnel client
cummand start http://localhost:3000
```

### Connect to an Existing Relay

If someone else is running the server (or it's deployed on Render), connect to it directly:

```bash
cummand start http://localhost:3000 --server wss://relay.example.com
```

## Dashboard

When you run `cummand start`, a live terminal dashboard shows real-time tunnel stats:

- **Status** — connection status (Online/Offline)
- **Tunnel URL** — the public URL for your tunnel
- **Uptime** — how long the tunnel has been active
- **Requests** — total request count
- **Data** — bytes sent through the tunnel
- **Latency** — round-trip time

The dashboard updates in-place (no screen flicker) using Rich's Live display.

## How It Works

When you run `cummand start http://localhost:3000`:

1. The client connects to the relay server via WebSocket
2. The server generates a unique 4-word code (e.g. `crimson-swift-falcon-river`)
3. The client receives the code and displays the tunnel URL
4. When someone visits `https://server.com/crimson-swift-falcon-river`, the server forwards the request through the WebSocket tunnel to the client
5. The client proxies the request to `http://localhost:3000/` and sends the response back

## URL Format

```bash
# Root page
https://server.com/crimson-swift-falcon-river

# Sub-page (links work naturally)
https://server.com/crimson-swift-falcon-river/about
https://server.com/crimson-swift-falcon-river/api/users
```

## Self-Hosting on Render

See [Deploy to Render](../README.md#self-hosting-deploy-to-render) in the main README.

## Makefile (Unix/macOS/WSL)

| Target    | Description                                      |
| --------- | ------------------------------------------------ |
| `install` | Production install                               |
| `dev`     | Editable install for development                 |
| `test`    | Run the test suite                               |
| `clean`   | Remove build artifacts (egg-info, __pycache__)   |

On Windows, run the commands directly:
- `pip install -e .`
- `pip install -e ".[dev]"`
- `python -m pytest tests/ -v`

## Code Words

Each tunnel gets a unique 4-word code in the format `color-adjective-animal-noun`:

- **100 colors** — crimson, amber, azure, coral, emerald, ...
- **100 adjectives** — swift, calm, brave, eager, silent, ...
- **100 animals** — falcon, tiger, otter, hawk, wolf, ...
- **100 nouns** — river, forest, summit, valley, meadow, ...

This gives **100 million unique combinations**.
