resource "google_cloud_run_v2_service" "tempus_vestis" {
  name                = "tempus-vestis"
  location            = var.region
  deletion_protection = false

  # Public by design (PORT-23) — browsers hit this directly. See iam.tf for the
  # allUsers run.invoker grant and knowledge/decisions.md for the org-policy
  # override that makes it possible.
  ingress = "INGRESS_TRAFFIC_ALL"

  template {
    service_account = google_service_account.tempus_vestis_run.email

    scaling {
      min_instance_count = 0
      max_instance_count = 1
    }

    # Denial-of-wallet control (2026-07-02 security audit): without this, Cloud
    # Run's default concurrency (80) means a single instance would happily
    # accept up to 80 simultaneous /recommend requests, each triggering a real
    # OpenAI call. 10 caps the worst-case burst cost per instance while still
    # being far above realistic personal-project traffic.
    max_instance_request_concurrency = 10

    # No vpc_access: this service uses Cloud Run's default internet egress. Phase
    # 2 (PORT-25) added public-internet dependencies (OpenAI, NWS) on top of the
    # existing auth-service call. Rather than route everything through the VPC
    # (egress=ALL_TRAFFIC) and pay for a Cloud NAT to give that VPC traffic an
    # internet path, the shared auth service was switched to ingress=ALL (still
    # IAM-gated), so its *.run.app endpoint is now reachable over the public path
    # like OpenAI/NWS/GCS. Nothing here needs the VPC anymore.
    # See knowledge/decisions.md 2026-07-02 and rw-gcp-shared-infa's.

    containers {
      name  = "tempus-vestis"
      image = "${var.region}-docker.pkg.dev/${var.project}/${data.terraform_remote_state.common.outputs.artifact_registry_repository_id}/tempus-vestis:latest"

      ports {
        container_port = 8080
      }

      # Phase 2 (PORT-30): the image now carries the full LangGraph/FAISS/OpenAI
      # stack, not just the Phase 1 proxy deps. 512Mi is too tight once
      # LangChain + faiss-cpu are imported; bumped to 1Gi. Only billed while an
      # instance is actually serving (min_instance_count = 0, cpu_idle = true).
      resources {
        limits = {
          cpu    = "1"
          memory = "1Gi"
        }
        cpu_idle          = true
        startup_cpu_boost = true
      }

      # Wider startup budget than Phase 1's ~32s (PORT-30): importing LangChain
      # + faiss and downloading the vectorstore from GCS on cold start takes
      # meaningfully longer than the old proxy-only image. ~5s + 12×10s ≈ 125s
      # before Cloud Run gives up. startup_cpu_boost above keeps that import
      # from being throttled to the idle CPU allocation.
      startup_probe {
        http_get {
          path = "/health"
          port = 8080
        }
        initial_delay_seconds = 5
        period_seconds        = 10
        failure_threshold     = 12
      }

      env {
        name  = "AUTH_SERVICE_URL"
        value = data.terraform_remote_state.auth.outputs.auth_service_url
      }

      # Where the container downloads the FAISS index to, and reads it from
      # (VECTORSTORE_PATH is consumed by src/core/rag.py). /tmp is the writable
      # in-memory filesystem on Cloud Run. (PORT-27)
      env {
        name  = "VECTORSTORE_BUCKET"
        value = google_storage_bucket.vectorstore.name
      }
      env {
        name  = "VECTORSTORE_PATH"
        value = "/tmp/vectorstore"
      }

      # OpenAI key sourced from Secret Manager at runtime via Cloud Run v2's
      # native secret support (PORT-28) — never a plaintext env value.
      env {
        name = "OPENAI_API_KEY"
        value_source {
          secret_key_ref {
            secret  = google_secret_manager_secret.openai_api_key.secret_id
            version = "latest"
          }
        }
      }
    }
  }
}
