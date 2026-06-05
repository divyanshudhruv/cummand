import tomllib
import tomli_w
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Optional


CONFIG_FILENAME = "cummand.config.toml"


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


def find_config() -> Optional[Path]:
    path = Path.cwd() / CONFIG_FILENAME
    return path if path.exists() else None


def read_config(path: Optional[Path] = None) -> CummandConfig:
    if path is None:
        path = find_config()
    cfg = CummandConfig()
    if path is None or not path.exists():
        return cfg
    raw = tomllib.loads(path.read_text(encoding="utf-8"))
    if "defaults" in raw:
            d = raw["defaults"]
            cfg.defaults.server_url = d.get("server_url", cfg.defaults.server_url)
            cfg.defaults.public_url = d.get("public_url", cfg.defaults.public_url)
            cfg.defaults.auto_open = d.get("auto_open", cfg.defaults.auto_open)
            cfg.defaults.log_level = d.get("log_level", cfg.defaults.log_level)
            cfg.defaults.retry_limit = d.get("retry_limit", cfg.defaults.retry_limit)
    if "auth" in raw:
        cfg.auth.token = raw["auth"].get("token", "")
    if "alias" in raw:
        for name, alias_data in raw["alias"].items():
            cfg.aliases[name] = AliasConfig(
                url=alias_data.get("url", ""),
                description=alias_data.get("description", ""),
            )
    return cfg


def write_config(cfg: CummandConfig, path: Optional[Path] = None) -> Path:
    if path is None:
        path = Path.cwd() / CONFIG_FILENAME
    data: dict = {}
    if cfg.defaults != DefaultsConfig():
        data["defaults"] = asdict(cfg.defaults)
    if cfg.auth.token:
        data["auth"] = asdict(cfg.auth)
    if cfg.aliases:
        data["alias"] = {}
        for name, alias in cfg.aliases.items():
            data["alias"][name] = asdict(alias)
    path.write_text(tomli_w.dumps(data), encoding="utf-8")
    return path


def add_alias(name: str, url: str, description: str = "", path: Optional[Path] = None) -> CummandConfig:
    cfg = read_config(path)
    cfg.aliases[name] = AliasConfig(url=url, description=description)
    write_config(cfg, path)
    return cfg


def remove_alias(name: str, path: Optional[Path] = None) -> CummandConfig:
    cfg = read_config(path)
    cfg.aliases.pop(name, None)
    write_config(cfg, path)
    return cfg


def set_option(key: str, value: str, path: Optional[Path] = None) -> CummandConfig:
    cfg = read_config(path)
    if key == "auth-token":
        cfg.auth.token = value
    elif key == "log-level":
        cfg.defaults.log_level = value
    elif key == "auto-open":
        cfg.defaults.auto_open = value.lower() in ("true", "1", "yes")
    elif key == "retry-limit":
        cfg.defaults.retry_limit = int(value)
    else:
        raise ValueError(f"Unknown option: {key}")
    write_config(cfg, path)
    return cfg
