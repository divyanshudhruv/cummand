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
