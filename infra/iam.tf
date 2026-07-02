resource "google_service_account" "tempus_vestis_run" {
  account_id   = "tempus-vestis-run"
  display_name = "Tempus Vestis Cloud Run service account"
}

# The auth service is ingress = INTERNAL_ONLY with Cloud Run IAM auth left on
# (see rw-gcp-shared-infa/knowledge/decisions.md 2026-07-02) — every caller,
# including this proxy, needs an explicit per-caller run.invoker grant.
# The auth service's short name/location aren't exposed as remote-state
# outputs (only its URL and DB name are), so they're hardcoded here to match
# rw-gcp-shared-infa/authentication/cloud_run.tf's resource name and region —
# tightly coupled by design, both are portfolio-shared us-central1 services.
resource "google_cloud_run_v2_service_iam_member" "tempus_vestis_can_invoke_auth" {
  project  = "rw-portfolio"
  name     = "authentication"
  location = var.region
  role     = "roles/run.invoker"
  member   = "serviceAccount:${google_service_account.tempus_vestis_run.email}"
}

# Read-only access to the vectorstore bucket only (PORT-27), scoped to this
# single bucket rather than a project-wide roles/storage.objectViewer grant —
# the container downloads index.faiss/index.pkl on startup, nothing more.
resource "google_storage_bucket_iam_member" "tempus_vestis_reads_vectorstore" {
  bucket = google_storage_bucket.vectorstore.name
  role   = "roles/storage.objectViewer"
  member = "serviceAccount:${google_service_account.tempus_vestis_run.email}"
}

# Public/unauthenticated by design (PORT-23) — this is the browser-facing UI.
# Only possible because of the rw-portfolio-scoped iam.allowedPolicyMemberDomains
# override; see knowledge/decisions.md (2026-07-02, "Override
# iam.allowedPolicyMemberDomains for rw-portfolio to allow a public Cloud Run
# service").
resource "google_cloud_run_v2_service_iam_member" "tempus_vestis_public_invoker" {
  name     = google_cloud_run_v2_service.tempus_vestis.name
  location = google_cloud_run_v2_service.tempus_vestis.location
  role     = "roles/run.invoker"
  member   = "allUsers"
}
