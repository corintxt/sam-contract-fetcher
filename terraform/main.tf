resource "google_storage_bucket" "contract_data" {
  name     = var.gcs_bucket_name
  location = var.region
  project  = var.project_id

  uniform_bucket_level_access = true
  
  lifecycle_rule {
    condition {
      age = 90
    }
    action {
      type = "Delete"
    }
  }
}

resource "google_cloud_run_service" "contract_fetcher" {
  name     = "contract-fetcher"
  location = var.region
  project  = var.project_id

  template {
    spec {
      containers {
        image = "gcr.io/${var.project_id}/contract-fetcher:latest"

        env {
          name  = "SAM_API_KEY"
          value = var.sam_api_key
        }

        env {
          name  = "GCS_BUCKET_NAME"
          value = var.gcs_bucket_name
        }
      }

      # Set the maximum number of instances
      max_instances = 1
    }
  }

  # Allow unauthenticated invocations
  autogenerate_revision_name = true
  traffic {
    percent         = 100
    latest_revision = true
  }
}

resource "google_cloud_scheduler_job" "daily_contract_fetch" {
  name        = "daily-contract-fetch"
  description = "Fetch contracts daily at 6 AM"
  schedule    = var.schedule
  time_zone   = "UTC"

  http_target {
    http_method = "POST"
    uri         = "${google_cloud_run_service.contract_fetcher.status[0].url}/fetch"

    oauth_token {
      service_account_email = var.service_account_email
    }
  }
}

output "cloud_run_url" {
  value = google_cloud_run_service.contract_fetcher.status[0].url
}