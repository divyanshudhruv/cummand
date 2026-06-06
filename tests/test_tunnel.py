from cummand.tunnel import TunnelSession


class FakeWS:
    def __init__(self):
        self.sent = []

    async def send(self, msg):
        self.sent.append(msg)

    async def recv(self):
        return b""


def test_tunnel_session_defaults():
    ws = FakeWS()
    sess = TunnelSession(code="test-code", local_port=3000, ws=ws)
    assert sess.code == "test-code"
    assert sess.local_port == 3000
    assert sess.request_count == 0
    assert sess.latency == 0.0
    assert sess.log_level == "info"


def test_tunnel_request_count():
    ws = FakeWS()
    sess = TunnelSession(code="test", local_port=3000, ws=ws)
    sess.record_request()
    sess.record_request()
    sess.record_request()
    assert sess.request_count == 3


def test_tunnel_path():
    ws = FakeWS()
    sess = TunnelSession(code="crimson-swift-falcon-river", local_port=3000, ws=ws)
    assert sess.tunnel_path == "/crimson-swift-falcon-river"
