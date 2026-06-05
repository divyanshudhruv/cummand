# CLI Reference

## cummand start

Start a tunnel to expose a local server.

```bash
cummand start [OPTIONS] [URL]
```

### Arguments

| Argument | Description                                                     |
| -------- | --------------------------------------------------------------- |
| `URL`    | Local URL to tunnel (ad-hoc mode), e.g. `http://localhost:3000` |

### Options

| Option          | Shorthand | Description                                         |
| --------------- | --------- | --------------------------------------------------- |
| `--alias`       | `-a`      | Profile alias from config file                      |
| `--server`      | `-s`      | Relay server URL (overrides config)                 |
| `--log-level`   | `-l`      | Log level: `debug` or `info` (default: from config) |
| `--retry-limit` | `-r`      | Max reconnection attempts (default: from config)    |

### Examples

```bash
# Ad-hoc: tunnel a local dev server
cummand start http://localhost:3000

# Profile: use a saved alias
cummand start --alias frontend

# With explicit server and debug logging
cummand start http://localhost:3000 --server wss://relay.example.com --log-level debug
```

---

## cummand config

Manage configuration profiles and settings.

### Commands

#### `cummand config list`

List all configured aliases in a table.

```bash
cummand config list
```

#### `cummand config add`

Add a new alias profile.

```bash
cummand config add --alias NAME --url URL [--desc DESCRIPTION]
```

| Option    | Shorthand | Required | Description         |
| --------- | --------- | -------- | ------------------- |
| `--alias` | `-a`      | Yes      | Alias name          |
| `--url`   | `-u`      | Yes      | Local URL to tunnel |
| `--desc`  | `-d`      | No       | Description         |

#### `cummand config remove`

Remove an alias profile.

```bash
cummand config remove --alias NAME
```

#### `cummand config set`

Set configuration options.

```bash
cummand config set [OPTIONS]
```

| Option              | Description                                                                                                                            |
| ------------------- | -------------------------------------------------------------------------------------------------------------------------------------- |
| `--auth-token KEY`  | Set auth token for server authentication                                                                                               |
| `--log-level LEVEL` | Set log level (`debug` or `info`)                                                                                                      |
| `--auto-open BOOL`  | Auto-open browser on tunnel start (`true` or `false`)                                                                                  |
| `--retry-limit N`   | Set max reconnection attempts                                                                                                          |
| `--server URL`      | Set default relay server URL (WebSocket)                                                                                               |
| `--public-url URL`  | Set public-facing URL (`{code}` replaced with tunnel code, e.g. `http://localhost:8080/{code}` or `https://myapp.onrender.com/{code}`) |

---

## cummand server start

Start the relay server.

```bash
cummand server start [OPTIONS]
```

| Option         | Shorthand | Default | Description                                                   |
| -------------- | --------- | ------- | ------------------------------------------------------------- |
| `--port`       | `-p`      | `8080`  | Port to listen on (HTTP + WebSocket both served on this port) |
| `--auth-token` |           | `""`    | Required client auth token (empty = no auth)                  |
| `--log-level`  | `-l`      | `info`  | Log level                                                     |

The server also reads these environment variables automatically:

| Env Var               | Overrides         |
| --------------------- | ----------------- |
| `PORT`                | `--port` default  |
| `CUMMAND_AUTH_TOKEN`  | `--auth-token` default |
