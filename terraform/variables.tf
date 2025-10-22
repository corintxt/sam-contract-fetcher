variable "project_id" {
  description = "The ID of the Google Cloud project"
  type        = string
}

variable "region" {
  description = "The region where the Cloud Run service will be deployed"
  type        = string
}

variable "gcs_bucket_name" {
  description = "The name of the Google Cloud Storage bucket for storing contract data"
  type        = string
}

variable "sam_api_key" {
  description = "The API key for accessing the SAM API"
  type        = string
}

variable "service_account_email" {
  description = "Service account email for Cloud Scheduler"
  type        = string
}

variable "schedule" {
  description = "The schedule for the Cloud Run job in cron format"
  type        = string
  default     = "0 6 * * *"  # Daily at 6 AM
}