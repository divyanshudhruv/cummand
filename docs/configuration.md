# Configuration

`cummand` uses a `cummand.config.toml` file in the **current working directory** (not a parent directory).

## File Location

The config file must be in the directory where you run the `cummand` command:

```bash
my-project/
├── cummand.config.toml    ← here
└── src/
    └── ...
```

## Reference

### `[defaults]`

Default settings used when no override is provided via CLI flags.

```toml
[defaults]
server_url = "ws://localhost:8080"
public_url = "http://{code}.localhost:8080"
auto-open = true
log-level = "info"
retry-limit = 5
```

| Field         | Type    | Default                             | Description                                |
| ------------- | ------- | ----------------------------------- | ------------------------------------------ |
| `server_url`  | string  | `"ws://localhost:8080"`             | Default relay server URL                   |
| `public_url`  | string  | `"http://{code}.localhost:8080"`    | Public URL template (`{code}` is replaced) |
| `auto-open`   | bool    | `true`                              | Open tunnel URL in browser automatically   |
| `log-level`   | string  | `"info"`                            | `"info"` or `"debug"`                      |
| `retry-limit` | integer | `5`                                 | Max reconnection attempts before giving up |

### `[auth]`

Authentication settings for connecting to a protected relay server.

```toml
[auth]
token = "sk_abc123..."
```

| Field   | Type   | Default | Description                     |
| ------- | ------ | ------- | ------------------------------- |
| `token` | string | `""`    | Auth token for the relay server |

### `[alias]`

Named profiles for frequently tunneled servers.

```toml
[alias.frontend]
url = "http://localhost:3000"
description = "Main Next.js app"

[alias.backend]
url = "http://localhost:8000"
description = "Python FastAPI service"
```

| Field         | Type   | Required | Description          |
| ------------- | ------ | -------- | -------------------- |
| `url`         | string | Yes      | Local URL to tunnel  |
| `description` | string | No       | Human-readable label |

## Example: Full Config

```toml
[defaults]
server_url = "wss://relay.example.com"
public_url = "https://relay.example.com/{code}"
auto-open = true
log-level = "info"
retry-limit = 5

[auth]
token = "sk_abc123..."

[alias.frontend]
url = "http://localhost:3000"
description = "Main Next.js app"

[alias.backend]
url = "http://localhost:8000"
description = "Python FastAPI service"

[alias.db-tunnel]
url = "http://localhost:5432"
description = "Postgres local interface"
```
