from pathlib import Path
from cummand.config import (
    read_config,
    write_config,
    add_alias,
    remove_alias,
    set_option,
    CummandConfig,
    DefaultsConfig,
    AuthConfig,
    AliasConfig,
)


def test_default_config(tmp_path: Path):
    cfg = read_config(tmp_path / "nonexistent.toml")
    assert cfg.defaults.server_url == "ws://localhost:8080"
    assert cfg.defaults.auto_open is True
    assert cfg.defaults.log_level == "info"
    assert cfg.defaults.retry_limit == 5
    assert cfg.auth.token == ""
    assert cfg.aliases == {}


def test_write_and_read_roundtrip(tmp_path: Path):
    cfg = CummandConfig()
    cfg.aliases["frontend"] = AliasConfig(url="http://localhost:3000", description="Test")
    path = tmp_path / "cummand.config.toml"
    write_config(cfg, path)
    assert path.exists()

    loaded = read_config(path)
    assert "frontend" in loaded.aliases
    assert loaded.aliases["frontend"].url == "http://localhost:3000"


def test_add_alias(tmp_path: Path):
    path = tmp_path / "cummand.config.toml"
    add_alias("test", "http://localhost:5000", "Test service", path)
    cfg = read_config(path)
    assert "test" in cfg.aliases
    assert cfg.aliases["test"].url == "http://localhost:5000"


def test_remove_alias(tmp_path: Path):
    path = tmp_path / "cummand.config.toml"
    add_alias("test", "http://localhost:5000", "", path)
    remove_alias("test", path)
    cfg = read_config(path)
    assert "test" not in cfg.aliases


def test_set_option_log_level(tmp_path: Path):
    path = tmp_path / "cummand.config.toml"
    write_config(CummandConfig(), path)
    set_option("log-level", "debug", path)
    cfg = read_config(path)
    assert cfg.defaults.log_level == "debug"


def test_set_option_auto_open(tmp_path: Path):
    path = tmp_path / "cummand.config.toml"
    write_config(CummandConfig(), path)
    set_option("auto-open", "false", path)
    cfg = read_config(path)
    assert cfg.defaults.auto_open is False


def test_set_option_retry_limit(tmp_path: Path):
    path = tmp_path / "cummand.config.toml"
    write_config(CummandConfig(), path)
    set_option("retry-limit", "10", path)
    cfg = read_config(path)
    assert cfg.defaults.retry_limit == 10


def test_set_option_auth_token(tmp_path: Path):
    path = tmp_path / "cummand.config.toml"
    write_config(CummandConfig(), path)
    set_option("auth-token", "sk_test", path)
    cfg = read_config(path)
    assert cfg.auth.token == "sk_test"


def test_get_field_prefers_kebab(tmp_path: Path):
    from cummand.config import _get_field
    d = {"log-level": "debug", "log_level": "info"}
    assert _get_field(d, "log_level") == "debug"


def test_get_field_falls_back_to_snake(tmp_path: Path):
    from cummand.config import _get_field
    d = {"log_level": "debug"}
    assert _get_field(d, "log_level") == "debug"


def test_get_field_returns_none_when_missing(tmp_path: Path):
    from cummand.config import _get_field
    d = {"other": "value"}
    assert _get_field(d, "log_level") is None


def test_get_field_uses_field_map(tmp_path: Path):
    from cummand.config import _get_field
    d = {"server-url": "ws://example.com"}
    assert _get_field(d, "server_url") == "ws://example.com"
