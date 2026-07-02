"""Phase 1 (PORT-18): minimal token-gated web front end for tempus-vestis.

The browser can't reach the auth service directly — it's Cloud Run
ingress=INTERNAL_ONLY (VPC-internal only), see
rw-gcp-shared-infa/knowledge/decisions.md (2026-07-02). This app proxies
POST /verify to it instead.

No LangGraph/RAG pipeline here by design (PORT-18 scope) — that's Phase 2.
"""

import os
from pathlib import Path

import httpx
from fastapi import FastAPI, Response
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel

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


async def _fetch_identity_token(client: httpx.AsyncClient) -> str | None:
    try:
        resp = await client.get(
            _METADATA_IDENTITY_URL,
            params={"audience": AUTH_SERVICE_URL},
            headers={"Metadata-Flavor": "Google"},
            timeout=1.5,
        )
        resp.raise_for_status()
        return resp.text
    except httpx.HTTPError:
        return None


app = FastAPI(title="tempus-vestis-phase1")


class VerifyRequest(BaseModel):
    token: str


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/")
def index():
    return FileResponse(STATIC_DIR / "index.html")


@app.post("/verify")
async def verify(body: VerifyRequest, response: Response):
    headers = {"X-Auth-Token": body.token}
    async with httpx.AsyncClient() as client:
        identity_token = await _fetch_identity_token(client)
        if identity_token:
            headers["Authorization"] = f"Bearer {identity_token}"

        try:
            upstream = await client.post(
                f"{AUTH_SERVICE_URL}/verify", headers=headers, timeout=10
            )
        except httpx.HTTPError:
            response.status_code = 502
            return {"error": "auth service unreachable"}

    if upstream.status_code == 200:
        return JSONResponse(upstream.json(), status_code=200)

    detail = "invalid, expired, or exhausted token"
    try:
        detail = upstream.json().get("detail", detail)
    except ValueError:
        pass
    return JSONResponse({"error": detail}, status_code=upstream.status_code)
