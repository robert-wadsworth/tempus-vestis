"""Unit tests for the token-gated proxy (PORT-20, PORT-26). Upstream auth-service
calls and the LangGraph pipeline are faked so these run without a live Cloud SQL
/ Cloud Run dependency or an OpenAI key.
"""

import os

os.environ.setdefault("AUTH_SERVICE_URL", "https://authentication.example.internal")

import httpx
from fastapi.testclient import TestClient

from app import main


class _FakeResponse:
    def __init__(self, status_code, json_body):
        self.status_code = status_code
        self._json = json_body

    def json(self):
        return self._json

    def raise_for_status(self):
        if self.status_code >= 400:
            raise httpx.HTTPStatusError("error", request=None, response=self)


class _FakeClient:
    """Sync stand-in for httpx.Client (used as a context manager)."""

    def __init__(self, get_response=None, get_raises=None, post_response=None, post_raises=None):
        self._get_response = get_response
        self._get_raises = get_raises
        self._post_response = post_response
        self._post_raises = post_raises
        self.post_headers = None

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False

    def get(self, *args, **kwargs):
        if self._get_raises:
            raise self._get_raises
        return self._get_response

    def post(self, *args, **kwargs):
        self.post_headers = kwargs.get("headers")
        if self._post_raises:
            raise self._post_raises
        return self._post_response


class _FakeGraph:
    """Stand-in for the compiled LangGraph; records the state it was invoked with."""

    def __init__(self, recommendations=None, raises=None):
        self._recommendations = recommendations
        self._raises = raises
        self.invoked_with = None

    def invoke(self, state):
        self.invoked_with = state
        if self._raises:
            raise self._raises
        return {**state, "recommendations": self._recommendations}


def _client():
    return TestClient(main.app)


def _patch_client(monkeypatch, fake):
    monkeypatch.setattr(main.httpx, "Client", lambda: fake)


def test_health():
    resp = _client().get("/health")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}


def test_index_serves_html():
    resp = _client().get("/")
    assert resp.status_code == 200
    assert "Tempus Vestis" in resp.text


def test_verify_success(monkeypatch):
    fake = _FakeClient(
        get_raises=httpx.ConnectError("no metadata server"),  # local dev: no GCP metadata
        post_response=_FakeResponse(200, {"valid": True, "uses_remaining": 3}),
    )
    _patch_client(monkeypatch, fake)

    resp = _client().post("/verify", json={"token": "sometoken"})
    assert resp.status_code == 200
    assert resp.json() == {"valid": True, "uses_remaining": 3}
    assert fake.post_headers == {"X-Auth-Token": "sometoken"}


def test_verify_adds_identity_token_when_available(monkeypatch):
    fake = _FakeClient(
        get_response=_FakeResponse(200, None),
        post_response=_FakeResponse(200, {"valid": True, "uses_remaining": 1}),
    )
    fake._get_response.text = "fake-id-token"
    _patch_client(monkeypatch, fake)

    resp = _client().post("/verify", json={"token": "sometoken"})
    assert resp.status_code == 200
    assert fake.post_headers == {
        "X-Auth-Token": "sometoken",
        "Authorization": "Bearer fake-id-token",
    }


def test_verify_rejected_by_auth_service(monkeypatch):
    fake = _FakeClient(
        get_raises=httpx.ConnectError("no metadata server"),
        post_response=_FakeResponse(401, {"detail": "invalid, expired, or exhausted token"}),
    )
    _patch_client(monkeypatch, fake)

    resp = _client().post("/verify", json={"token": "bogus"})
    assert resp.status_code == 401
    assert resp.json() == {"error": "invalid, expired, or exhausted token"}


def test_verify_auth_service_unreachable(monkeypatch):
    fake = _FakeClient(
        get_raises=httpx.ConnectError("no metadata server"),
        post_raises=httpx.ConnectError("connection refused"),
    )
    _patch_client(monkeypatch, fake)

    resp = _client().post("/verify", json={"token": "sometoken"})
    assert resp.status_code == 502
    assert resp.json() == {"error": "auth service unreachable"}


def test_recommend_success(monkeypatch):
    fake = _FakeClient(
        get_raises=httpx.ConnectError("no metadata server"),
        post_response=_FakeResponse(200, {"valid": True, "uses_remaining": 2}),
    )
    _patch_client(monkeypatch, fake)
    graph = _FakeGraph(recommendations="Pack a warm coat and layers.")
    monkeypatch.setattr(main, "_get_graph", lambda: graph)

    resp = _client().post(
        "/recommend", json={"token": "good", "query": "What should I pack for Chicago in 7 days?"}
    )
    assert resp.status_code == 200
    assert resp.json() == {
        "recommendation": "Pack a warm coat and layers.",
        "uses_remaining": 2,
    }
    # The pipeline was invoked with the user's query, and only one token use was
    # consumed (a single /verify call).
    assert graph.invoked_with == {"query": "What should I pack for Chicago in 7 days?"}


def test_recommend_rejected_token_skips_pipeline(monkeypatch):
    fake = _FakeClient(
        get_raises=httpx.ConnectError("no metadata server"),
        post_response=_FakeResponse(401, {"detail": "invalid, expired, or exhausted token"}),
    )
    _patch_client(monkeypatch, fake)

    def _must_not_run():
        raise AssertionError("pipeline must not run on a rejected token")

    monkeypatch.setattr(main, "_get_graph", _must_not_run)

    resp = _client().post("/recommend", json={"token": "bogus", "query": "anything"})
    assert resp.status_code == 401
    assert resp.json() == {"error": "invalid, expired, or exhausted token"}


def test_recommend_pipeline_failure_returns_502(monkeypatch):
    fake = _FakeClient(
        get_raises=httpx.ConnectError("no metadata server"),
        post_response=_FakeResponse(200, {"valid": True, "uses_remaining": 4}),
    )
    _patch_client(monkeypatch, fake)
    graph = _FakeGraph(raises=RuntimeError("OpenAI down"))
    monkeypatch.setattr(main, "_get_graph", lambda: graph)

    resp = _client().post("/recommend", json={"token": "good", "query": "Chicago in 7 days"})
    assert resp.status_code == 502
    assert "error" in resp.json()
