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

    # Needed to reach the VPC-internal auth service. Egress must be ALL_TRAFFIC,
    # not PRIVATE_RANGES_ONLY: the auth service's *.run.app hostname resolves to
    # a public Google-managed IP (not RFC1918), so PRIVATE_RANGES_ONLY sends
    # that call out the normal internet path instead of the VPC NIC — Cloud
    # Run's ingress=INTERNAL_ONLY then silently 404s it (found the hard way in
    # the PORT-24 smoke test; see knowledge/decisions.md 2026-07-02).
    vpc_access {
      network_interfaces {
        network    = data.terraform_remote_state.common.outputs.vpc_name
        subnetwork = data.terraform_remote_state.common.outputs.subnetwork_name
      }
      egress = "ALL_TRAFFIC"
    }

    containers {
      name  = "tempus-vestis"
      image = "${var.region}-docker.pkg.dev/${var.project}/${data.terraform_remote_state.common.outputs.artifact_registry_repository_id}/tempus-vestis:latest"

      ports {
        container_port = 8080
      }

      resources {
        limits = {
          cpu    = "1"
          memory = "512Mi"
        }
        cpu_idle          = true
        startup_cpu_boost = true
      }

      startup_probe {
        http_get {
          path = "/health"
          port = 8080
        }
        initial_delay_seconds = 2
        period_seconds        = 5
        failure_threshold     = 6
      }

      env {
        name  = "AUTH_SERVICE_URL"
        value = data.terraform_remote_state.auth.outputs.auth_service_url
      }
    }
  }
}
