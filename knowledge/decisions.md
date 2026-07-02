# Decision Log

> Record non-obvious decisions and the reasoning behind them. Newest at top.

---

### 2026-07-02 — Cloud Run→Cloud Run private calls need `egress = ALL_TRAFFIC` + Private Google Access on, not `PRIVATE_RANGES_ONLY`

**Decision:** `infra/cloud_run.tf`'s `vpc_access.egress` is `ALL_TRAFFIC`, not
`PRIVATE_RANGES_ONLY` (what `authentication/cloud_run.tf` uses for its own,
different, egress need). The shared VPC subnet
(`rw-portfolio-subnet-us-central1`) must also have Private Google Access **on**
persistently — it was left disabled after the PORT-17 smoke-test cleanup, which
broke this the first time PORT-24 was tested.

**Why:** Found by debugging a real PORT-24 failure, in two stages:
1. With `PRIVATE_RANGES_ONLY`, calls from this service to the auth service's
   `*.run.app` URL got an instant `404` from Cloud Run's ingress guard (Cloud Run
   returns 404, not 403, for ingress-disallowed requests — deliberately, so it
   doesn't reveal the service exists). Root cause: `*.run.app` resolves to a
   public Google-managed IP, not an RFC1918 address, so `PRIVATE_RANGES_ONLY`
   egress sent that traffic out the normal internet path instead of the VPC NIC,
   and `authentication`'s `ingress = INTERNAL_ONLY` rejected it. Confirmed via
   Cloud Logging: zero request log entries on the `authentication` service for
   these calls — they never arrived. Switched to `ALL_TRAFFIC`.
2. `ALL_TRAFFIC` alone then hung and timed out (502, latency pinned to our own
   httpx client timeout) — because Private Google Access was off on the subnet
   (disabled at the end of the PORT-17 smoke-test cleanup, on the assumption it
   was only needed temporarily for that VM). Direct VPC egress relies on Private
   Google Access being enabled to resolve/reach Google-managed endpoints.
   Re-enabled it, this time **permanently** — `tempus-vestis` is a standing
   service, not a throwaway smoke-test VM, so this isn't optional cleanup here.

Contrast with `authentication/cloud_run.tf`'s `PRIVATE_RANGES_ONLY`: that egress
is for reaching Cloud SQL's *private IP*, which genuinely is RFC1918 — a
different traffic pattern that `PRIVATE_RANGES_ONLY` correctly handles. The
"public Google-managed IP" problem only applies to calling *other Cloud Run
services* by their `*.run.app` hostname.

**Note:** immediately after the subnet-level PGA change, the very next request
still failed the same way (still a ~10-21s timeout) before a subsequent request
succeeded — looked like a stale warm instance or brief propagation delay, not a
config error. One of those transitional failed client-side requests appears to
have still completed server-side (the test token's use count was already
decremented by the time a response was successfully observed). Not a concern for
this app, but worth knowing: a slow/timed-out response from this proxy doesn't
guarantee the underlying auth-service call didn't succeed.

---

### 2026-07-02 — Override `iam.allowedPolicyMemberDomains` for `rw-portfolio` to allow a public Cloud Run service

**Decision:** PORT-23 requires `tempus-vestis`'s Phase 1 service to be publicly
reachable (browsers hit it directly), which needs an `allUsers` `roles/run.invoker`
IAM binding. The org's `iam.allowedPolicyMemberDomains` policy (see
`rw-gcp-shared-infa/knowledge/decisions.md` 2026-07-02, and
`memory/gcp_org_policy_constraints.md`) blocks that by default. Applied a
project-scoped override:
```
gcloud resource-manager org-policies set-policy policy.yaml --project=rw-portfolio
# constraint: constraints/iam.allowedPolicyMemberDomains
# listPolicy:
#   allValues: ALLOW
```
Org default (all other projects) is untouched — this only affects `rw-portfolio`.

**Why:** Unlike the `authentication` service, there's no VPC-internal alternative here
— the entire point of Phase 1 is that arbitrary browsers, not just VPC-resident
callers, need to reach the token-entry UI. The GCP API for this constraint doesn't
support a narrower "just allow `allUsers`" exception; `listPolicy.allowedValues` only
accepts specific Cloud Identity customer IDs, so the only override mechanism is the
all-or-nothing `allValues: ALLOW`/`DENY` toggle. This is a single-owner personal
portfolio project — there's no other team or org tenant whose access this guardrail
was protecting here, so accepting the broader (project-scoped, not org-scoped) relaxation
was judged worth it rather than adding real infrastructure (an External HTTPS Load
Balancer, ~$18-25/month) purely to avoid it.

**Alternatives rejected:** External HTTPS Load Balancer fronting an IAM-only Cloud Run
backend (LB invokes Cloud Run with its own identity, so `allUsers` is never granted
anywhere) — more production-realistic and avoids touching the org policy at all, but
real ongoing cost and meaningfully more Terraform for a portfolio demo whose actual
risk (this project, this owner) doesn't justify it.

---

### 2026-07-02 — Never `pip install` into the main `.venv` for anything outside `pyproject.toml`; `main.py` forces UTF-8 stdout

**Decision:** Two small fixes from getting PORT-19 (local dev verification) to actually
pass on Windows:
1. `main.py` now does `sys.stdout.reconfigure(encoding="utf-8")` near the top if the
   console isn't already UTF-8, so `uv run python main.py` doesn't crash with
   `UnicodeEncodeError` on stock Windows PowerShell (default `cp1252` codepage can't
   encode the CLI banner's box-drawing/emoji characters).
2. Never install `app/requirements.txt` (the Phase 1 web service's pinned deps, e.g.
   `pydantic==2.10.4`) into this repo's main `.venv`. Test `app/` in its own throwaway
   venv instead.

**Why:** Point 2 is a real incident, not a hypothetical: a stray
`uv pip install -r app/requirements.txt` into the main `.venv` conflicted with the
newer `pydantic` pulled in transitively by LangChain/LangGraph and left
`pydantic_core` partially uninstalled (Windows file-lock error mid-removal), breaking
`import pydantic` for the whole `src/` app. Fixed by deleting `.venv` (gitignored,
disposable) and re-running `uv sync`. This is exactly the dependency-isolation the
"Phase 1 web app lives in `app/`" decision below was meant to guarantee — the mistake
was testing both halves in the same environment instead of keeping them separate.

---

### 2026-07-02 — Phase 1 proxy authenticates to the auth service via metadata-server identity token, with a fast local-dev fallback

**Decision:** `app/main.py`'s `POST /verify` handler tries to fetch a Google ID token
scoped to `AUTH_SERVICE_URL` from the Cloud Run metadata server
(`http://metadata.google.internal/.../identity?audience=...`) and, if that succeeds,
sends it as `Authorization: Bearer <token>` alongside the app's own `X-Auth-Token`
header. The metadata call uses a 1.5s timeout and swallows `httpx.HTTPError`, so local
dev (no metadata server) just skips the header instead of hanging or crashing.

**Why:** The `authentication` service is `ingress = INTERNAL_ONLY` with Cloud Run IAM
auth left on (per-caller `run.invoker` grants, not `allUsers` — the org's
domain-restricted-sharing policy blocks `allUsers` entirely). See
`rw-gcp-shared-infa/knowledge/decisions.md` (2026-07-02, "authentication service access
control") for the full org-policy background. That means any caller — including this
proxy — needs a Google ID token in `Authorization` to get past Cloud Run's IAM layer,
on top of the app's own `X-Auth-Token`. This is the exact mechanism already proven
working in the PORT-17 smoke test (a VM fetching an identity token from its own
metadata server); Cloud Run exposes the same metadata server to its containers, so the
pattern carries over directly. PORT-23's Terraform will grant this service's own SA
`roles/run.invoker` on the auth service, mirroring what the smoke-test VM's SA got.

**Alternatives rejected:** Hardcoding a service-to-service secret or API key — rejected
because it duplicates the IAM identity Cloud Run already provides for free via the
attached service account, and would be one more secret to manage for no real benefit at
this scale.

---

### 2026-07-02 — Phase 1 web app lives in `app/`, isolated from the existing `src/` LangGraph app

**Decision:** All Phase 1 (PORT-18) code — `app/main.py`, `app/static/index.html`,
`app/requirements.txt`, `Dockerfile` — is new and does not import from `src/` or reuse
`pyproject.toml`'s dependency set. The Docker image installs only
`fastapi`/`uvicorn`/`httpx`/`pydantic` from `app/requirements.txt`, not the
LangGraph/FAISS/OpenAI stack.

**Why:** PORT-18's explicit scope is "confirm the full token auth flow works end-to-end
in GCP... before any application changes are made to tempus-vestis" — the LangGraph
pipeline (`POST /recommend`, FAISS vectorstore, `OPENAI_API_KEY`) is Phase 2. Keeping
the two dependency trees separate means the Phase 1 image stays small and doesn't need
an OpenAI key or GCS bucket to build or run, and Phase 2 can add the heavier stack later
without having to touch or re-verify the token-gating logic.

**Alternatives rejected:** Building `app/` on top of the full `pyproject.toml`
dependency set from day one — rejected as unnecessary weight for a service that, in
Phase 1, never calls OpenAI or LangGraph at all.
