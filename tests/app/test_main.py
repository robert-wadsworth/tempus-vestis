"""Unit tests for the Phase 1 proxy (PORT-20). Upstream auth-service calls are
faked so these run without a live Cloud SQL / Cloud Run dependency.
"""

import os

os.environ.setdefault("AUTH_SERVICE_URL", "https://authentication.example.internal")

import httpx
import pytest
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


class _FakeAsyncClient:
    def __init__(self, get_response=None, get_raises=None, post_response=None, post_raises=None):
        self._get_response = get_response
        self._get_raises = get_raises
        self._post_response = post_response
        self._post_raises = post_raises
        self.post_headers = None

    async def __aenter__(self):
        return self

    async def __aexit__(self, *exc):
        return False

    async def get(self, *args, **kwargs):
        if self._get_raises:
            raise self._get_raises
        return self._get_response

    async def post(self, *args, **kwargs):
        self.post_headers = kwargs.get("headers")
        if self._post_raises:
            raise self._post_raises
        return self._post_response


def _client():
    return TestClient(main.app)


def test_health():
    resp = _client().get("/health")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}


def test_index_serves_html():
    resp = _client().get("/")
    assert resp.status_code == 200
    assert "Tempus Vestis" in resp.text


def test_verify_success(monkeypatch):
    fake = _FakeAsyncClient(
        get_raises=httpx.ConnectError("no metadata server"),  # local dev: no GCP metadata
        post_response=_FakeResponse(200, {"valid": True, "uses_remaining": 3}),
    )
    monkeypatch.setattr(main.httpx, "AsyncClient", lambda: fake)

    resp = _client().post("/verify", json={"token": "sometoken"})
    assert resp.status_code == 200
    assert resp.json() == {"valid": True, "uses_remaining": 3}
    assert fake.post_headers == {"X-Auth-Token": "sometoken"}


def test_verify_adds_identity_token_when_available(monkeypatch):
    fake = _FakeAsyncClient(
        get_response=_FakeResponse(200, None),
        post_response=_FakeResponse(200, {"valid": True, "uses_remaining": 1}),
    )
    fake._get_response.text = "fake-id-token"
    monkeypatch.setattr(main.httpx, "AsyncClient", lambda: fake)

    resp = _client().post("/verify", json={"token": "sometoken"})
    assert resp.status_code == 200
    assert fake.post_headers == {
        "X-Auth-Token": "sometoken",
        "Authorization": "Bearer fake-id-token",
    }


def test_verify_rejected_by_auth_service(monkeypatch):
    fake = _FakeAsyncClient(
        get_raises=httpx.ConnectError("no metadata server"),
        post_response=_FakeResponse(401, {"detail": "invalid, expired, or exhausted token"}),
    )
    monkeypatch.setattr(main.httpx, "AsyncClient", lambda: fake)

    resp = _client().post("/verify", json={"token": "bogus"})
    assert resp.status_code == 401
    assert resp.json() == {"error": "invalid, expired, or exhausted token"}


def test_verify_auth_service_unreachable(monkeypatch):
    fake = _FakeAsyncClient(
        get_raises=httpx.ConnectError("no metadata server"),
        post_raises=httpx.ConnectError("connection refused"),
    )
    monkeypatch.setattr(main.httpx, "AsyncClient", lambda: fake)

    resp = _client().post("/verify", json={"token": "sometoken"})
    assert resp.status_code == 502
    assert resp.json() == {"error": "auth service unreachable"}
