"""Tests for server routing logic — _extract_code_and_path and tunnel fallback."""

from cummand.server import _extract_code_and_path


class FakeRequest:
    def __init__(self, host: str, path: str):
        self.host = host
        self.path = path


def test_extract_code_from_subdomain():
    req = FakeRequest("crimson-swift-falcon-river.localhost", "/")
    code, remaining = _extract_code_and_path(req)
    assert code == "crimson-swift-falcon-river"
    assert remaining == "/"


def test_extract_code_from_subdomain_with_path():
    req = FakeRequest("mycode.localhost", "/about")
    code, remaining = _extract_code_and_path(req)
    assert code == "mycode"
    assert remaining == "/about"


def test_extract_code_from_path():
    req = FakeRequest("localhost:8080", "/mycode")
    code, remaining = _extract_code_and_path(req)
    assert code == "mycode"
    assert remaining == ""


def test_extract_code_from_path_with_remainder():
    req = FakeRequest("localhost:8080", "/mycode/api/users")
    code, remaining = _extract_code_and_path(req)
    assert code == "mycode"
    assert remaining == "/api/users"


def test_extract_code_from_subdomain_with_port():
    req = FakeRequest("mycode.localhost", "/test")
    code, remaining = _extract_code_and_path(req)
    assert code == "mycode"
    assert remaining == "/test"


def test_extract_code_127_dot_0_dot_0_dot_1_subdomain():
    req = FakeRequest("mycode.127.0.0.1", "/")
    code, remaining = _extract_code_and_path(req)
    assert code == "mycode"
    assert remaining == "/"


def test_extract_code_no_code_in_path_or_host():
    req = FakeRequest("example.com", "/")
    code, remaining = _extract_code_and_path(req)
    assert code == ""
    assert remaining == ""


def test_extract_code_from_empty_host():
    req = FakeRequest("", "/some-code")
    code, remaining = _extract_code_and_path(req)
    assert code == "some-code"
    assert remaining == ""


# _rate_limited unit tests

from unittest.mock import patch

from cummand.server import _rate_limited, _connection_counts, RATE_LIMIT


def setup_method():
    _connection_counts.clear()


@patch("cummand.server.time.time")
def test_rate_limited_allows_up_to_limit(mock_time):
    mock_time.return_value = 1000.0
    _connection_counts.clear()
    ip = "1.2.3.4"
    for i in range(RATE_LIMIT):
        assert not _rate_limited(ip), f"call {i + 1} should be allowed"
    assert _rate_limited(ip), "call after limit should be blocked"


@patch("cummand.server.time.time")
def test_rate_limited_window_expiry(mock_time):
    _connection_counts.clear()
    ip = "5.6.7.8"
    mock_time.return_value = 1000.0
    for _ in range(RATE_LIMIT):
        _rate_limited(ip)
    assert _rate_limited(ip)
    # advance past the window — old timestamps are filtered out
    mock_time.return_value = 2000.0
    assert not _rate_limited(ip), "window expired, should allow"


@patch("cummand.server.time.time")
def test_rate_limited_different_ips_independent(mock_time):
    mock_time.return_value = 1000.0
    _connection_counts.clear()
    ip_a = "10.0.0.1"
    ip_b = "10.0.0.2"
    # exhaust ip_a
    for _ in range(RATE_LIMIT):
        _rate_limited(ip_a)
    assert _rate_limited(ip_a)
    # ip_b is unaffected
    assert not _rate_limited(ip_b)
