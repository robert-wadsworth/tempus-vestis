# tempus-vestis

AI-powered wardrobe consultant (LangGraph agent + RAG over a wardrobe knowledge base,
NWS weather API). Originally a standalone local CLI (`main.py`, `src/`) — see `README.md`
for that half of the project.

## Web service (`app/`) — Phase 1 (PORT-18) + Phase 2 (PORT-25)

A Cloud Run service that gates access with the shared portfolio `authentication`
service (`rw-gcp-shared-infa/authentication/`) and serves wardrobe recommendations.

- `app/main.py` — FastAPI app:
  - `GET /`, `GET /health`
  - `POST /verify` — forwards a token to the auth service as `X-Auth-Token`, plus a
    Google ID token fetched from the Cloud Run metadata server when available
  - `POST /recommend` (Phase 2) — verifies-and-consumes the token **once**, then runs
    the `src/` LangGraph/RAG pipeline and returns `{recommendation, uses_remaining}`.
    Skips the pipeline entirely on a rejected token (no OpenAI cost). Shares the
    `_verify_and_consume()` helper with `/verify`.
- `app/static/index.html` — the entire frontend, single file (token + query form)
- `Dockerfile` — installs `.[web]` (full pipeline + web layer; see `knowledge/decisions.md`)
- `infra/` — Terraform root module: Cloud Run, the vectorstore GCS bucket, and the
  OpenAI-key Secret Manager secret
- `scripts/seed_vectorstore.py` — manual step to (re)build the FAISS index and upload
  it to GCS; run when `data/wardrobe_rules.txt` changes

**Phase 2 flipped the Phase 1 isolation:** `app/` now shares `src/`'s
LangGraph/FAISS/OpenAI dependency tree (unified in `pyproject.toml`'s `web` extra), and
the service now has a real per-request OpenAI cost. See `knowledge/decisions.md`.

## Relationship to the shared portfolio infra

Reads the auth service's URL via Terraform `terraform_remote_state` from
`rw-gcp-shared-infa`, the same pattern `mlflow/` and `authentication/` use — see that
repo's `CLAUDE.md` for the shared conventions (naming, cost discipline, security
defaults) this repo also follows.

## Testing

`pyproject.toml` pytest config covers both halves: `src/` (the original CLI, tests
under `tests/core/`, `tests/tools/`) and `app/` (Phase 1 web service, tests under
`tests/app/`). Run everything with `pytest`; Phase 1 tests fake the upstream auth-service
HTTP calls, so they don't need a live Cloud SQL / Cloud Run connection.
