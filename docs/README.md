# Cummand Documentation

- [CLI Reference](cli.md) — all commands and options
- [Configuration](configuration.md) — config file reference

## Installation

### Usage (remove dev files)
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

`cummand` is open-source ngrok alternative. It works in two parts:

1. **Server** — a public relay server that accepts HTTP connections and forwards them through WebSocket tunnels
2. **Client** — runs on your dev machine, connects to the server, and relays requests to your local server

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

## Code Words

Each tunnel gets a unique 4-word code in the format `color-adjective-animal-noun`:

- **100 colors** — crimson, amber, azure, coral, emerald, ...
- **100 adjectives** — swift, calm, brave, eager, silent, ...
- **100 animals** — falcon, tiger, otter, hawk, wolf, ...
- **100 nouns** — river, forest, summit, valley, meadow, ...

This gives **100 million unique combinations**.
