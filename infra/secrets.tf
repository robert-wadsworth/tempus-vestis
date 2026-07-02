# OpenAI API key in Secret Manager (PORT-28) — the first real Secret Manager
# usage in this portfolio. (mlflow authenticates to Cloud SQL via IAM, not a
# stored password, despite the stale Confluence MLflow page; that's corrected
# separately, not here.)
resource "google_secret_manager_secret" "openai_api_key" {
  secret_id = "tempus-vestis-openai-api-key"

  replication {
    auto {}
  }
}

resource "google_secret_manager_secret_version" "openai_api_key" {
  secret      = google_secret_manager_secret.openai_api_key.id
  secret_data = var.openai_api_key
}

# Scoped to this one secret, not a project-wide secretAccessor grant — the
# Cloud Run service account can read only this key.
resource "google_secret_manager_secret_iam_member" "tempus_vestis_reads_openai_key" {
  secret_id = google_secret_manager_secret.openai_api_key.secret_id
  role      = "roles/secretmanager.secretAccessor"
  member    = "serviceAccount:${google_service_account.tempus_vestis_run.email}"
}
