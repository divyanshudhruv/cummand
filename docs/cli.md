# CLI Reference

## cummand tunnel

Start a tunnel to expose a local server.

```bash
cummand tunnel [OPTIONS] [URL]
```

### Arguments

| Argument | Description                                                     |
| -------- | --------------------------------------------------------------- |
| `URL`    | Local URL to tunnel, e.g. `http://localhost:3000` (ad-hoc mode) |

### Options

| Option          | Shorthand | Description                                         |
| --------------- | --------- | --------------------------------------------------- |
| `--alias`       | `-a`      | Use a saved alias profile from config               |
| `--server`      | `-s`      | Relay server URL (overrides config)                 |
| `--auth-token`  |           | Auth token for relay server (overrides config)      |
| `--log-level`   | `-l`      | Log level: `debug` or `info` (default: from config) |
| `--retry-limit` | `-r`      | Max reconnection attempts (default: from config)    |
| `--global`      | `-g`      | Use global config at `~/.cummand/`                  |

Global options available on all commands:

| Option      | Shorthand | Description           |
| ----------- | --------- | --------------------- |
| `--version` | `-V`      | Show version and exit |

### Examples

```bash
# Use the public relay (default — no --server needed)
cummand tunnel http://localhost:3000

# Profile: use a saved alias from config
cummand tunnel --alias frontend

# Use a custom server
cummand tunnel http://localhost:3000 --server wss://my-relay.com

# Use global config and debug logging
cummand tunnel --alias api --global --log-level debug
```

---

## cummand serve

Start the relay server (HTTP + WebSocket on the same port).
Can also start a tunnel client in the same process with `--tunnel`.

```bash
cummand serve [OPTIONS]
```

### Options

| Option         | Shorthand | Default | Description                                                           |
| -------------- | --------- | ------- | --------------------------------------------------------------------- |
| `--port`       | `-p`      | `8080`  | Port to listen on                                                     |
| `--auth-token` |           | `""`    | Require auth token from clients                                       |
| `--tunnel`     | `-t`      | `None`  | Also tunnel this local URL in the same process (single-terminal mode) |
| `--log-level`  | `-l`      | `info`  | Log level: `debug` or `info`                                          |

### Single-Terminal Workflow (What It Is)

Normally, `cummand` needs two separate processes:

1. A **relay server** that forwards HTTP requests via WebSocket (started with `cummand serve`)
2. A **tunnel client** that connects your local server to the relay (started with `cummand tunnel`)

This means two terminals: one for the server, one for the client.

**Single-terminal mode** (`cummand serve --tunnel`) runs both in the same process using `asyncio.gather()`. The relay server handles inbound HTTP/WebSocket connections on its port, and the tunnel client simultaneously connects to that server and proxies your local app. You see logs from both in one terminal.

```bash
# One command — starts relay on :8080 AND tunnels localhost:3000
cummand serve --tunnel http://localhost:3000
```

Use this for local development. Use two terminals when you need the server to keep running while restarting the client, or when server and client are on different machines.

### Environment Variables

| Env Var               | Default | Description                                 |
| --------------------- | ------- | ------------------------------------------- |
| `PORT`                | `8080`  | Server port                                 |
| `CUMMAND_AUTH_TOKEN`  | `""`    | Require auth token from clients             |
| `CUMMAND_MAX_TUNNELS` | `500`   | Max simultaneous tunnels (global cap)       |
| `CUMMAND_RATE_LIMIT`  | `5`     | Max WebSocket connections per IP per window |
| `CUMMAND_RATE_WINDOW` | `60`    | Rate limit window in seconds                |

### Health Check

The server exposes `GET /health` returning JSON with status, version, and tunnel count:

```bash
curl https://cummand.onrender.com/health
# {"status":"ok","version":"0.4.0","tunnels":0}
```

---

## cummand config

Manage configuration aliases and defaults.

### `cummand config init`

Create a default `cummand.config.toml`.

```bash
cummand config init [--global|-g]
```

| Option     | Shorthand | Description                                                 |
| ---------- | --------- | ----------------------------------------------------------- |
| `--global` | `-g`      | Install in `~/.cummand/` for global use across all projects |

The global config at `~/.cummand/cummand.config.toml` is used as fallback when no local config exists.

### `cummand config list`

List all configured aliases in a table.

```bash
cummand config list [--global|-g]
```

### `cummand config add`

Add a new alias profile.

```bash
cummand config add --alias NAME --url URL [--desc DESCRIPTION] [--global|-g]
```

| Option     | Shorthand | Required | Description         |
| ---------- | --------- | -------- | ------------------- |
| `--alias`  | `-a`      | Yes      | Alias name          |
| `--url`    | `-u`      | Yes      | Local URL to tunnel |
| `--desc`   | `-d`      | No       | Description         |
| `--global` | `-g`      | No       | Use global config   |

### `cummand config remove`

Remove an alias profile.

```bash
cummand config remove --alias NAME [--global|-g]
```

### `cummand config set`

Set a single configuration option.

```bash
cummand config set <key> <value> [--global|-g]
```

| Positional | Description                                                                                   |
| ---------- | --------------------------------------------------------------------------------------------- |
| `key`      | Config key: `auth-token`, `server-url`, `public-url`, `log-level`, `auto-open`, `retry-limit` |
| `value`    | Config value (bool values: `true`/`false`, number values: integer strings)                    |

Examples:

```bash
cummand config set log-level debug
cummand config set server-url wss://relay.example.com
cummand config set auto-open false
cummand config set retry-limit 10
cummand config set auth-token sk_abc123
cummand config set server-url wss://my-relay.com --global
```

---

## Global Config (`--global`, `-g`)

Every command that reads or writes config supports `--global` / `-g` to target
`~/.cummand/cummand.config.toml` instead of the local `./cummand.config.toml`.

| Command                 | `-g` Support |
| ----------------------- | ------------ |
| `cummand tunnel`        | Yes          |
| `cummand config init`   | Yes          |
| `cummand config list`   | Yes          |
| `cummand config add`    | Yes          |
| `cummand config remove` | Yes          |
| `cummand config set`    | Yes          |
