# Cummand Documentation

- [CLI Reference](cli.md) — all commands and options
- [Configuration](configuration.md) — config file reference
- [Contributing](../CONTRIBUTING.md) — development guide

## Quick Start

```bash
git clone https://github.com/divyanshudhruv/cummand.git
cd cummand
pip install .
cummand config init --global
cummand tunnel http://localhost:3000
```

Share the public URL shown in your terminal. Press `Ctrl+C` to stop.

## How It Works

`cummand` is an open-source ngrok alternative. You connect a **client** on your machine to a **relay server** (public or self-hosted). The server assigns a 4-word code like `crimson-swift-falcon-river` and forwards HTTP requests through a WebSocket tunnel to your local server.

```bash
# Your tunnel URL
https://cummand.onrender.com/crimson-swift-falcon-river      → localhost:3000/
https://cummand.onrender.com/crimson-swift-falcon-river/about → localhost:3000/about
```

## Dashboard

When you run `cummand tunnel`, a live terminal dashboard shows real-time tunnel stats:

- **Status** — connection status (Online/Offline)
- **Tunnel URL** — the public URL for your tunnel
- **Uptime** — how long the tunnel has been active
- **Requests** — total request count
- **Data** — bytes sent through the tunnel
- **Latency** — round-trip time

## Code Words

Each tunnel gets a unique 4-word code in the format `color-adjective-animal-noun`:

- 100 colors, 100 adjectives, 100 animals, 100 nouns → **100 million unique combinations**.

## Self-Hosting

Your own relay server on Render, a VPS, or any cloud provider:

```bash
git clone https://github.com/divyanshudhruv/cummand.git
cd cummand
pip install .
cummand serve --port 8080
```

Then on your dev machine:

```bash
cummand config set server-url wss://your-server.com
cummand config set public-url https://your-server.com/{code}
```

### Deploy to Render

1. Fork the repo
2. Render → New Web Service → connect your fork
3. Build: `pip install .` — Start: `cummand serve`
4. Set env vars:

   | Key | Value | Required |
   |---|---|---|
   | `CUMMAND_AUTH_TOKEN` | `your-secret-token` | Recommended |
   | `CUMMAND_MAX_TUNNELS` | `500` | Optional |
   | `CUMMAND_RATE_LIMIT` | `5` | Optional |
   | `CUMMAND_RATE_WINDOW` | `60` | Optional |

5. Health check: `GET /health` returns `{"status":"ok","version":"0.4.0","tunnels":0}`

## Troubleshooting

### Tunnel won't connect

- **Public server down?** Check `https://cummand.onrender.com/health`.
- **Wrong server URL?** Verify `server-url` in config or pass `--server`.
- **Auth token mismatch?** Set `CUMMAND_AUTH_TOKEN` or pass `--auth-token`.
- **Is your local app running?** The tunnel proxies to `localhost:<port>`.
- **Check the logs:** Run with `--log-level debug` for detail.

### Config not found

- `cummand` looks for `cummand.config.toml` in the current directory, then falls back to `~/.cummand/cummand.config.toml`.
- Run `cummand config init --global` to create one.
