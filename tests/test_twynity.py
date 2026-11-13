"""Verify Twynity\u2019s OAuth external-connection routes (Interconnector \u00a710.3).

Covers: manifest declares oauth, login mints a state + returns the authorize
URL, token-callback exchanges code\u2192tokens and stores them (single-use
state), logout deletes, and /external-connection/me reports status.
"""

import pytest
from fastmcp import FastMCP
from starlette.testclient import TestClient

from app.auth import TwynityIdentity
from app.twynity import register_routes


@pytest.fixture
def unauthenticated_app():
    """No auth attached \u2014 manifest/health should work without a token."""
    mcp = FastMCP("test_server")
    register_routes(mcp)
    return mcp.http_app()


def test_manifest_returns_expected_shape(unauthenticated_app):
    client = TestClient(unauthenticated_app)
    response = client.get("/api/v1/.well-known/mcp.json")
    assert response.status_code == 200
    body = response.json()
    assert "name" in body
    assert "version" in body


def test_health_endpoint_returns_ok(unauthenticated_app):
    client = TestClient(unauthenticated_app)
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


class FakeStore:
    def __init__(self):
        self.sessions = {}
        self.tokens = {}

    async def save_session(self, state, session_data):
        self.sessions[state] = session_data

    async def get_session(self, state):
        return self.sessions.get(state)

    async def delete_session(self, state):
        self.sessions.pop(state, None)

    async def save_token(self, user_id, persona_id, token):
        self.tokens[(user_id, persona_id)] = token
        return "id"

    async def get_token(self, user_id, persona_id):
        return self.tokens.get((user_id, persona_id))

    async def public_metadata(self, user_id, persona_id):
        if (user_id, persona_id) in self.tokens:
            return {"id": "tok-id", "has_access_token": True, "has_refresh_token": True}
        return None

    async def delete_token(self, user_id, persona_id):
        if (user_id, persona_id) in self.tokens:
            del self.tokens[(user_id, persona_id)]
            return True
        return False


def test_manifest_declares_oauth(unauthenticated_app):
    response = TestClient(unauthenticated_app).get("/api/v1/.well-known/mcp.json")
    ec = response.json()["external_connections"]
    assert ec["oauth"]["provider"] == "clickup"
    assert ec["api_key"] is None
    assert ec["project"] is None


def test_login_mints_state_and_returns_authorize_url(monkeypatch):
    import app.twynity as routes

    identity = TwynityIdentity(user_id="user-1", persona_id="persona-1")
    store = FakeStore()
    monkeypatch.setattr(routes, "get_identity", lambda _request: _identity(identity))
    monkeypatch.setattr(routes, "get_active_store", lambda: store)
    mcp = FastMCP("test_login")
    register_routes(mcp)
    client = TestClient(mcp.http_app())
    headers = {"Authorization": "Bearer verified-by-test", "Persona-Id": "persona-1"}

    response = client.get(
        "/api/v1/auth/clickup/login",
        params={"redirect_uri": "https://twynity-dev.mcp.4th-ir.com/clickup/api/v1/callback"},
        headers=headers,
    )
    assert response.status_code == 200
    body = response.json()
    assert "authorization_url" in body
    assert "state" in body
    # The state was stored with the user/persona.
    assert store.sessions[body["state"]]["user_id"] == "user-1"
    assert store.sessions[body["state"]]["persona_id"] == "persona-1"


def test_token_callback_exchanges_and_stores(monkeypatch):
    import app.twynity as routes

    identity = TwynityIdentity(user_id="user-1", persona_id="persona-1")
    store = FakeStore()
    monkeypatch.setattr(routes, "get_identity", lambda _request: _identity(identity))
    monkeypatch.setattr(routes, "get_active_store", lambda: store)
    # Stub the provider token exchange.
    async def fake_exchange(code, redirect_uri):
        assert code == "the-code"
        return {"access_token": "at-new", "refresh_token": "rt-new", "expires_in": 3600}
    monkeypatch.setattr(routes, "_exchange_code", fake_exchange)

    mcp = FastMCP("test_callback")
    register_routes(mcp)
    client = TestClient(mcp.http_app())
    headers = {"Authorization": "Bearer verified-by-test", "Persona-Id": "persona-1"}

    # Pre-seed the state that login would have created.
    store.save_session_sync = None
    import asyncio
    asyncio.get_event_loop_policy()
    # Save a session directly (the login step is tested separately).
    _run(store.save_session("state-x", {"user_id": "user-1", "persona_id": "persona-1"}))

    response = client.post(
        "/api/v1/auth/clickup/token-callback",
        params={
            "redirect_uri": "https://cb.example",
            "code": "the-code",
            "state": "state-x",
        },
        headers=headers,
    )
    assert response.status_code == 200
    assert response.json() == {"connected": True}
    # Token stored for the right identity; session consumed (single-use).
    assert store.tokens[("user-1", "persona-1")]["access_token"] == "at-new"
    assert "state-x" not in store.sessions
    # /external-connection/me now reports connected.
    assert client.get("/api/v1/external-connection/me", headers=headers).json() == {"connected": True}


def test_token_callback_rejects_bad_state(monkeypatch):
    import app.twynity as routes

    identity = TwynityIdentity(user_id="user-1", persona_id="persona-1")
    store = FakeStore()
    monkeypatch.setattr(routes, "get_identity", lambda _request: _identity(identity))
    monkeypatch.setattr(routes, "get_active_store", lambda: store)
    mcp = FastMCP("test_callback_bad")
    register_routes(mcp)
    client = TestClient(mcp.http_app())
    headers = {"Authorization": "Bearer verified-by-test", "Persona-Id": "persona-1"}

    response = client.post(
        "/api/v1/auth/clickup/token-callback",
        params={"redirect_uri": "https://cb.example", "code": "the-code", "state": "missing"},
        headers=headers,
    )
    assert response.status_code == 400
    assert "invalid_state" in response.text


def test_logout_deletes_token(monkeypatch):
    import app.twynity as routes

    identity = TwynityIdentity(user_id="user-1", persona_id="persona-1")
    store = FakeStore()
    store.tokens[("user-1", "persona-1")] = {"access_token": "at", "refresh_token": "rt"}
    monkeypatch.setattr(routes, "get_identity", lambda _request: _identity(identity))
    monkeypatch.setattr(routes, "get_active_store", lambda: store)
    mcp = FastMCP("test_logout")
    register_routes(mcp)
    client = TestClient(mcp.http_app())
    headers = {"Authorization": "Bearer verified-by-test", "Persona-Id": "persona-1"}

    response = client.post("/api/v1/auth/clickup/logout", headers=headers)
    assert response.status_code == 200
    assert response.json() == {"disconnected": True}
    assert ("user-1", "persona-1") not in store.tokens


async def _identity(value):
    return value


def _run(coro):
    """Run an awaitable in a fresh event loop (test helper)."""
    import asyncio
    loop = asyncio.new_event_loop()
    try:
        loop.run_until_complete(coro)
    finally:
        loop.close()
