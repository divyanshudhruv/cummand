# Configuration

`cummand` uses a `cummand.config.toml` file. It looks for one in two locations:

1. **Current working directory** (highest priority)
2. **Global fallback** at `~/.cummand/cummand.config.toml`

## File Locations

### Local config (per-project)

Place it in your project root where you run `cummand`:

```bash
my-project/
├── cummand.config.toml    ← local config
└── src/
    └── ...
```

### Global config (all projects)

Install a global config that applies to all projects when no local config exists:

```bash
cummand config init --global
# Creates ~/.cummand/cummand.config.toml
```

## Reference

### `[defaults]`

Default settings used when no override is provided via CLI flags.

```toml
[defaults]
server-url = "wss://cummand.onrender.com"
public-url = "https://cummand.onrender.com/{code}"
auto-open = true
log-level = "info"
retry-limit = 5
```

| Field         | Type    | Default                                 | Description                                                              |
| ------------- | ------- | --------------------------------------- | ------------------------------------------------------------------------ |
| `server-url`  | string  | `"wss://cummand.onrender.com"`          | Default relay server URL (public)                                        |
| `public-url`  | string  | `"https://cummand.onrender.com/{code}"` | Public URL template — `{code}` is replaced with the tunnel's 4-word code |
| `auto-open`   | bool    | `true`                                  | Open tunnel URL in browser automatically                                 |
| `log-level`   | string  | `"info"`                                | `"info"` or `"debug"`                                                    |
| `retry-limit` | integer | `5`                                     | Max reconnection attempts before giving up                               |

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

## Understanding `{code}`

The `public-url` setting uses `{code}` as a placeholder. When a tunnel starts, it gets a unique 4-word code (like `crimson-swift-falcon-river`). The `{code}` in the URL template is replaced with that code.

- If `public-url = "http://{code}.localhost:8080"` and your code is `crimson-swift-falcon-river`, the tunnel URL becomes `http://crimson-swift-falcon-river.localhost:8080`
- On a deployed server: `https://your-server.com/{code}` → `https://your-server.com/crimson-swift-falcon-river`

## Example: Full Config

```toml
[defaults]
server-url = "wss://cummand.onrender.com"
public-url = "https://cummand.onrender.com/{code}"
auto-open = true
log-level = "info"
retry-limit = 5

[alias.frontend]
url = "http://localhost:3000"
description = "Main Next.js app"

[alias.backend]
url = "http://localhost:8000"
description = "Python FastAPI service"
```
