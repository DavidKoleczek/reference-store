"""Who may reach the app on the local network: by address, by `Host`, and by key."""

from fastapi import FastAPI
from fastapi.responses import PlainTextResponse
import pytest
from starlette.testclient import TestClient

from reference_store.app.network import KEY_COOKIE, Machine, judge
from reference_store.app.pages import Guard

KEY = "the-key"
HERE = Machine(
    addresses=frozenset({"127.0.0.1", "192.168.1.20"}),
    names=frozenset({"127.0.0.1", "192.168.1.20", "localhost", "desk", "desk.local"}),
)


@pytest.mark.parametrize(
    ("client", "host", "cookie", "given", "allowed", "keep_key"),
    [
        # This machine needs no key, by loopback or by its own address.
        ("127.0.0.1", "127.0.0.1:8795", None, None, True, False),
        ("192.168.1.20", "192.168.1.20:8795", None, None, True, False),
        ("::ffff:127.0.0.1", "localhost:8795", None, None, True, False),
        # Another device needs the key, kept as a cookie the first time it comes in the URL.
        ("192.168.1.31", "192.168.1.20:8795", None, None, False, False),
        ("192.168.1.31", "192.168.1.20:8795", None, KEY, True, True),
        ("192.168.1.31", "192.168.1.20:8795", KEY, None, True, False),
        ("192.168.1.31", "192.168.1.20:8795", "old-key", "wrong", False, False),
        ("10.0.0.7", "desk.local:8795", KEY, None, True, False),
        ("172.20.1.2", "desk:8795", KEY, None, True, False),
        ("169.254.3.4", "192.168.1.20", KEY, None, True, False),
        # Nothing from outside the local network, key or not.
        ("8.8.8.8", "192.168.1.20:8795", KEY, None, False, False),
        ("172.32.0.1", "192.168.1.20:8795", KEY, None, False, False),
        (None, "192.168.1.20:8795", KEY, None, False, False),
        # A name that isn't this machine's, as a website's would be.
        ("127.0.0.1", "example.com:8795", None, None, False, False),
        ("192.168.1.31", "attacker.example:8795", KEY, None, False, False),
        ("127.0.0.1", None, None, None, False, False),
    ],
)
def test_only_the_local_network_with_the_key_is_let_in(
    client: str | None, host: str | None, cookie: str | None, given: str | None, allowed: bool, keep_key: bool
) -> None:
    verdict = judge(client, host, cookie, given, KEY, HERE)
    assert (verdict.allowed, verdict.keep_key) == (allowed, keep_key)
    assert verdict.allowed or verdict.reason


def test_a_device_trades_the_key_in_its_address_for_a_cookie() -> None:
    page = FastAPI()
    page.get("/")(lambda: PlainTextResponse("the app"))
    device = TestClient(
        Guard(page, KEY, HERE),
        base_url="http://192.168.1.20:8795",
        client=("192.168.1.31", 50000),
        follow_redirects=False,
    )
    assert device.get("/").status_code == 403
    traded = device.get(f"/?key={KEY}&view=files")
    assert (traded.status_code, traded.headers["location"]) == (303, "/?view=files")
    assert device.cookies[KEY_COOKIE] == KEY
    assert device.get("/").text == "the app"
