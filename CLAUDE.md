# tempus-vestis

AI-powered wardrobe consultant (LangGraph agent + RAG over a wardrobe knowledge base,
NWS weather API). Originally a standalone local CLI (`main.py`, `src/`) — see `README.md`
for that half of the project.

## Phase 1 (PORT-18): token-gated web front end

Deploying a minimal Cloud Run service that gates access with the shared portfolio
`authentication` service (`rw-gcp-shared-infa/authentication/`), before any web-facing
LangGraph work happens. Lives entirely in `app/` — deliberately does not import
anything from `src/` or install the LangGraph/FAISS dependency stack (see
`app/requirements.txt` vs. root `pyproject.toml`).

- `app/main.py` — FastAPI proxy: `GET /`, `GET /health`, `POST /verify` (forwards to
  the auth service as `X-Auth-Token`, plus a Google ID token fetched from the Cloud Run
  metadata server when available — see `knowledge/decisions.md`)
- `app/static/index.html` — the entire frontend, single file
- `Dockerfile` — Phase 1 image only (`python:3.11-slim` + `app/requirements.txt`)
- `infra/` — Terraform root module for the Phase 1 Cloud Run deployment (PORT-23)

Phase 2 (out of scope for now): wiring `POST /recommend` to the LangGraph pipeline,
GCS bucket for the FAISS index, Secret Manager for `OPENAI_API_KEY`.

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
