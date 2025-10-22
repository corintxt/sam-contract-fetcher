output "cloud_run_service_url" {
  value = google_cloud_run_service.contract_fetcher.status[0].url
  description = "URL of the deployed Cloud Run service"
}

output "gcs_bucket_name" {
  value = google_storage_bucket.contract_data.name
  description = "Name of the GCS bucket for contract data"
}

output "scheduler_job_name" {
  value = google_cloud_scheduler_job.daily_contract_fetch.name
  description = "Name of the Cloud Scheduler job"
}