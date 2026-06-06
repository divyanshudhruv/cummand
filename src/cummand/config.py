"""Configuration management — read, write, and validate TOML config files."""

import tomllib
import tomli_w
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Optional


CONFIG_FILENAME = "cummand.config.toml"
GLOBAL_CONFIG_DIR = ".cummand"


DEFAULT_FIELD_MAP: dict[str, str] = {
    "server_url": "server-url",
    "public_url": "public-url",
    "auto_open": "auto-open",
    "log_level": "log-level",
    "retry_limit": "retry-limit",
}


def _get_field(d: dict, field: str) -> object:
    """Read a field from a TOML dict, supporting snake_case and kebab-case keys."""
    toml_key = DEFAULT_FIELD_MAP.get(field, field)
    if toml_key in d:
        return d[toml_key]
    return d.get(field)


def get_global_config_path() -> Path:
    """Return the path to the global config file (~/.cummand/cummand.config.toml)."""
    return Path.home() / GLOBAL_CONFIG_DIR / CONFIG_FILENAME


DEFAULT_CONFIG_CONTENT = """\
[defaults]
server-url = "ws://localhost:8080"
public-url = "http://{code}.localhost:8080"
auto-open = true
log-level = "info"
retry-limit = 5

[auth]
token = ""
"""


@dataclass
class AliasConfig:
    url: str
    description: str = ""


@dataclass
class DefaultsConfig:
    server_url: str = "ws://localhost:8080"
    public_url: str = "http://{code}.localhost:8080"
    auto_open: bool = True
    log_level: str = "info"
    retry_limit: int = 5


@dataclass
class AuthConfig:
    token: str = ""


@dataclass
class CummandConfig:
    defaults: DefaultsConfig = field(default_factory=DefaultsConfig)
    auth: AuthConfig = field(default_factory=AuthConfig)
    aliases: dict[str, AliasConfig] = field(default_factory=dict)


def find_config(global_: bool = False) -> Optional[Path]:
    """Locate the nearest config file (cwd first, then global fallback)."""
    if global_:
        path = get_global_config_path()
        return path if path.exists() else None
    path = Path.cwd() / CONFIG_FILENAME
    if path.exists():
        return path
    global_path = get_global_config_path()
    return global_path if global_path.exists() else None


def read_config(path: Optional[Path] = None, global_: bool = False) -> CummandConfig:
    """Read and parse a TOML config file into a CummandConfig dataclass."""
    if path is None:
        path = find_config(global_=global_)
    cfg = CummandConfig()
    if path is None or not path.exists():
        return cfg
    raw = tomllib.loads(path.read_text(encoding="utf-8"))
    if "defaults" in raw:
        d = raw["defaults"]
        for py_field in ("server_url", "public_url", "log_level"):
            val = _get_field(d, py_field)
            if val is not None:
                setattr(cfg.defaults, py_field, val)
        auto = _get_field(d, "auto_open")
        if isinstance(auto, bool):
            cfg.defaults.auto_open = auto
        retry = _get_field(d, "retry_limit")
        if retry is not None:
            cfg.defaults.retry_limit = int(retry)
    if "auth" in raw:
        cfg.auth.token = raw["auth"].get("token", "")
    if "alias" in raw:
        for name, alias_data in raw["alias"].items():
            cfg.aliases[name] = AliasConfig(
                url=alias_data.get("url", ""),
                description=alias_data.get("description", ""),
            )
    return cfg


def _resolve_path(path: Optional[Path], global_: bool = False) -> Path:
    """Return the config path — cwd by default, global if requested."""
    if path:
        return path
    return get_global_config_path() if global_ else Path.cwd() / CONFIG_FILENAME


def write_config(cfg: CummandConfig, path: Optional[Path] = None, global_: bool = False) -> Path:
    """Write a CummandConfig to a TOML config file."""
    path = _resolve_path(path, global_)
    data: dict = {}
    if cfg.defaults != DefaultsConfig():
        defaults_dict = {}
        for py_field in DEFAULT_FIELD_MAP:
            val = getattr(cfg.defaults, py_field)
            if val != getattr(DefaultsConfig(), py_field):
                defaults_dict[DEFAULT_FIELD_MAP[py_field]] = val
        if defaults_dict:
            data["defaults"] = defaults_dict
    if cfg.auth.token:
        data["auth"] = asdict(cfg.auth)
    if cfg.aliases:
        data["alias"] = {}
        for name, alias in cfg.aliases.items():
            data["alias"][name] = asdict(alias)
    path.write_text(tomli_w.dumps(data), encoding="utf-8")
    return path


def add_alias(name: str, url: str, description: str = "", path: Optional[Path] = None, global_: bool = False) -> CummandConfig:
    """Add a new alias profile to the config file."""
    cfg = read_config(path, global_=global_)
    cfg.aliases[name] = AliasConfig(url=url, description=description)
    write_config(cfg, path, global_=global_)
    return cfg


def remove_alias(name: str, path: Optional[Path] = None, global_: bool = False) -> CummandConfig:
    """Remove an alias profile from the config file."""
    cfg = read_config(path, global_=global_)
    cfg.aliases.pop(name, None)
    write_config(cfg, path, global_=global_)
    return cfg


def set_option(key: str, value: str, path: Optional[Path] = None, global_: bool = False) -> CummandConfig:
    """Set a single config option."""
    cfg = read_config(path, global_=global_)
    if key == "auth-token":
        cfg.auth.token = value
    elif key == "server-url":
        cfg.defaults.server_url = value
    elif key == "public-url":
        cfg.defaults.public_url = value
    elif key == "log-level":
        cfg.defaults.log_level = value
    elif key == "auto-open":
        cfg.defaults.auto_open = value.lower() in ("true", "1", "yes")
    elif key == "retry-limit":
        cfg.defaults.retry_limit = int(value)
    else:
        raise ValueError(f"Unknown option: {key}")
    write_config(cfg, path, global_=global_)
    return cfg


def init_config(path: Optional[Path] = None, global_: bool = False) -> Path:
    """Create a default config file at the specified path."""
    if path is None:
        path = get_global_config_path() if global_ else Path.cwd() / CONFIG_FILENAME
    if global_:
        path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(DEFAULT_CONFIG_CONTENT, encoding="utf-8")
    return path
