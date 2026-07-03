"""Token-gated web front end for tempus-vestis.

Phase 1 (PORT-18) was a thin proxy that only verified tokens. Phase 2 (PORT-25)
adds POST /recommend, which verifies-and-consumes a token and then runs the
existing LangGraph/RAG pipeline from src/ to produce a packing recommendation.

The browser can't reach the auth service directly — it's Cloud Run
ingress=INTERNAL_ONLY (VPC-internal only), see
rw-gcp-shared-infa/knowledge/decisions.md (2026-07-02). This app proxies the
verify call to it instead, attaching a Google ID token minted from the Cloud
Run metadata server so it gets past the auth service's Cloud Run IAM layer.
"""

import os
from contextlib import asynccontextmanager
from dataclasses import dataclass
from pathlib import Path

import httpx
from fastapi import FastAPI, Request
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address

AUTH_SERVICE_URL = os.environ["AUTH_SERVICE_URL"].rstrip("/")
STATIC_DIR = Path(__file__).parent / "static"

# Metadata-server call to mint a Google ID token scoped to the auth service,
# same mechanism used by the smoke-test VM. Only reachable on GCP (Cloud Run
# attaches the metadata server automatically); a short timeout lets local dev
# (no metadata server, and no IAM auth on a bare `uvicorn` run of the auth
# service) fail fast and just skip the header instead of hanging.
_METADATA_IDENTITY_URL = (
    "http://metadata.google.internal/computeMetadata/v1/instance/"
    "service-accounts/default/identity"
)

_INDEX_FILES = ("index.faiss", "index.pkl")

# Compiled LangGraph pipeline, built once on startup and reused. Kept module-
# level so sync request handlers (run in FastAPI's threadpool) don't each
# recompile it.
_graph = None


def _fetch_identity_token(client: httpx.Client) -> str | None:
    try:
        resp = client.get(
            _METADATA_IDENTITY_URL,
            params={"audience": AUTH_SERVICE_URL},
            headers={"Metadata-Flavor": "Google"},
            timeout=1.5,
        )
        resp.raise_for_status()
        return resp.text
    except httpx.HTTPError:
        return None


@dataclass
class _AuthResult:
    """Outcome of a verify-and-consume call to the auth service."""

    status_code: int
    body: dict

    @property
    def accepted(self) -> bool:
        # The auth service returns 200 + valid=True only when the token was
        # valid and a use was actually consumed. Anything else (401/403 with an
        # error detail, or an unreachable-service 502) means don't proceed.
        return self.status_code == 200 and self.body.get("valid") is True


def _verify_and_consume(token: str) -> _AuthResult:
    """Verify a token via the auth service, consuming one use.

    Shared by both /verify and /recommend so the two never drift apart or use
    two token-uses for one request. Synchronous on purpose (see /recommend).
    """
    headers = {"X-Auth-Token": token}
    with httpx.Client() as client:
        identity_token = _fetch_identity_token(client)
        if identity_token:
            headers["Authorization"] = f"Bearer {identity_token}"

        try:
            upstream = client.post(
                f"{AUTH_SERVICE_URL}/verify", headers=headers, timeout=10
            )
        except httpx.HTTPError:
            return _AuthResult(status_code=502, body={"error": "auth service unreachable"})

    if upstream.status_code == 200:
        return _AuthResult(status_code=200, body=upstream.json())

    detail = "invalid, expired, or exhausted token"
    try:
        detail = upstream.json().get("detail", detail)
    except ValueError:
        pass
    return _AuthResult(status_code=upstream.status_code, body={"error": detail})


def _ensure_vectorstore() -> None:
    """Download the FAISS index from GCS into VECTORSTORE_PATH on startup.

    Only runs on Cloud Run (VECTORSTORE_BUCKET set); local dev and tests use the
    checked-out data/vectorstore/ and skip this. Fails loudly if the download
    fails — deliberately does NOT fall back to rebuilding the index locally,
    which would need OPENAI_API_KEY and incur embedding cost on every cold start.
    """
    bucket_name = os.getenv("VECTORSTORE_BUCKET")
    if not bucket_name:
        return

    dest = Path(os.getenv("VECTORSTORE_PATH", "data/vectorstore"))
    if all((dest / name).exists() for name in _INDEX_FILES):
        return

    dest.mkdir(parents=True, exist_ok=True)

    from google.cloud import storage

    bucket = storage.Client().bucket(bucket_name)
    for name in _INDEX_FILES:
        bucket.blob(name).download_to_filename(str(dest / name))


def _get_graph():
    global _graph
    if _graph is None:
        # Imported lazily so /health and /verify (and the test suite) don't pull
        # in the heavy LangChain/FAISS stack unless a recommendation is needed.
        from core.graph import build_wardrobe_graph

        _graph = build_wardrobe_graph()
    return _graph


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Fetch the vectorstore and warm the graph before serving. Cloud Run's
    # startup probe covers this window, so a bad vectorstore fails the deploy
    # loudly rather than surfacing as a 5xx on the first user request.
    _ensure_vectorstore()
    _get_graph()
    yield


app = FastAPI(title="tempus-vestis", lifespan=lifespan)

# Denial-of-wallet control (2026-07-02 security audit): /verify is unauthenticated
# by design (that's the point of it), so without a limit here it could be hammered
# with garbage tokens at no cost to the caller, each attempt still costing a round
# trip to the auth service + Cloud SQL. /recommend gets a tighter limit since each
# accepted request costs real OpenAI spend. In-memory storage is fine because
# max_instance_count = 1 (infra/cloud_run.tf) — there's only ever one instance to
# keep state in, so no Redis/shared backend is needed.
limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)


class VerifyRequest(BaseModel):
    token: str


class RecommendRequest(BaseModel):
    token: str
    query: str


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/")
def index():
    return FileResponse(STATIC_DIR / "index.html")


@app.post("/verify")
@limiter.limit("20/minute")
def verify(request: Request, body: VerifyRequest):
    result = _verify_and_consume(body.token)
    return JSONResponse(result.body, status_code=result.status_code)


@app.post("/recommend")
@limiter.limit("10/minute")
def recommend(request: Request, body: RecommendRequest):
    # Verify+consume first. On any failure, return the same error shape /verify
    # uses and stop here — no pipeline run, so an invalid/exhausted token never
    # incurs OpenAI cost.
    result = _verify_and_consume(body.token)
    if not result.accepted:
        return JSONResponse(result.body, status_code=result.status_code)

    # The graph routes weather/non-US failures to a friendly user-facing message
    # (WEATHER_ERROR_MESSAGE) rather than raising, so those come back as a normal
    # 200 recommendation. The try/except is only for genuinely unexpected
    # failures (e.g. OpenAI outage) — the token use is already spent by now, so
    # surface a clean 502 instead of a raw stack trace.
    try:
        state = _get_graph().invoke({"query": body.query})
    except Exception:
        return JSONResponse(
            {"error": "The recommendation service failed. Please try again."},
            status_code=502,
        )

    return {
        "recommendation": state.get("recommendations") or "",
        "uses_remaining": result.body.get("uses_remaining"),
    }
