#!/bin/bash

# Load environment variables from .env file
if [ -f .env ]; then
    echo "📝 Loading configuration from .env file..."
    export $(grep -v '^#' .env | xargs)
else
    echo "❌ Error: .env file not found!"
    echo "Please create a .env file with required variables:"
    echo "  - SAM_API_KEY"
    echo "  - GCS_BUCKET_NAME"
    echo "  - PROJECT_ID"
    echo "  - REGION"
    exit 1
fi

# Configuration
export JOB_NAME=${JOB_NAME:-contract-fetcher-job}
export LOG_LEVEL=${LOG_LEVEL:-INFO}

# Validate required variables
if [ -z "$PROJECT_ID" ] || [ -z "$REGION" ] || [ -z "$SAM_API_KEY" ] || [ -z "$GCS_BUCKET_NAME" ]; then
    echo "❌ Error: Missing required environment variables!"
    echo "Please ensure your .env file contains:"
    echo "  - PROJECT_ID"
    echo "  - REGION"
    echo "  - SAM_API_KEY"
    echo "  - GCS_BUCKET_NAME"
    exit 1
fi

# Email configuration (optional)
SEND_EMAILS=${SEND_EMAILS:-false}
if [ "$SEND_EMAILS" = "true" ]; then
    if [ -z "$MAILGUN_API_KEY" ] || [ -z "$MAILGUN_DOMAIN" ] || [ -z "$NOTIFICATION_EMAIL" ]; then
        echo "⚠️  Warning: Email notifications enabled but missing configuration!"
        echo "Please ensure your .env file contains:"
        echo "  - MAILGUN_API_KEY"
        echo "  - MAILGUN_DOMAIN"
        echo "  - NOTIFICATION_EMAIL"
        echo "Continuing deployment without email functionality..."
        SEND_EMAILS=false
    fi
fi

echo "🚀 Starting deployment to Google Cloud..."
echo "   Project: ${PROJECT_ID}"
echo "   Region: ${REGION}"
echo "   Job: ${JOB_NAME}"

# Step 1: Enable required APIs
echo "📋 Enabling required APIs..."
gcloud services enable \
  cloudbuild.googleapis.com \
  run.googleapis.com \
  cloudscheduler.googleapis.com

# Step 2: Build and push the container
echo "🏗️  Building container image..."
gcloud builds submit --tag gcr.io/${PROJECT_ID}/${JOB_NAME}

# Step 3: Deploy as Cloud Run Job (not Service)
echo "☁️  Deploying as Cloud Run Job..."
# Build environment variables string
ENV_VARS="SAM_API_KEY=${SAM_API_KEY},GCS_BUCKET_NAME=${GCS_BUCKET_NAME},PROJECT_ID=${PROJECT_ID},REGION=${REGION},LOG_LEVEL=${LOG_LEVEL},SEND_EMAILS=${SEND_EMAILS}"

if [ "$SEND_EMAILS" = "true" ]; then
    ENV_VARS="${ENV_VARS},MAILGUN_API_KEY=${MAILGUN_API_KEY},MAILGUN_DOMAIN=${MAILGUN_DOMAIN},NOTIFICATION_EMAIL=${NOTIFICATION_EMAIL}"
fi

gcloud run jobs deploy ${JOB_NAME} \
  --image gcr.io/${PROJECT_ID}/${JOB_NAME} \
  --region ${REGION} \
  --set-env-vars "${ENV_VARS}" \
  --memory 512Mi \
  --task-timeout 900

# Step 4: Create service account for Cloud Scheduler
echo "👤 Creating service account..."
gcloud iam service-accounts create cloud-scheduler \
  --display-name "Cloud Scheduler Service Account" \
  --project ${PROJECT_ID} 2>/dev/null || echo "Service account already exists"

# Step 5: Grant Cloud Run invoker role
echo "🔐 Setting up permissions..."
gcloud run jobs add-iam-policy-binding ${JOB_NAME} \
  --member=serviceAccount:cloud-scheduler@${PROJECT_ID}.iam.gserviceaccount.com \
  --role=roles/run.invoker \
  --region=${REGION}

# Step 6: Create Cloud Scheduler job
echo "⏰ Setting up Cloud Scheduler..."
gcloud scheduler jobs delete contract-fetcher-daily \
  --location=${REGION} \
  --quiet 2>/dev/null || echo "No existing scheduler job to delete"

gcloud scheduler jobs create http contract-fetcher-daily \
  --location=${REGION} \
  --schedule="0 6 * * *" \
  --uri="https://${REGION}-run.googleapis.com/apis/run.googleapis.com/v1/namespaces/${PROJECT_ID}/jobs/${JOB_NAME}:run" \
  --http-method=POST \
  --oauth-service-account-email=cloud-scheduler@${PROJECT_ID}.iam.gserviceaccount.com \
  --time-zone="America/New_York"

echo ""
echo "✅ Deployment complete!"
echo ""
echo "📊 Configuration Summary:"
echo "  - Job Name: ${JOB_NAME}"
echo "  - Schedule: Daily at 6:00 AM EST"
echo "  - Storage: gs://${GCS_BUCKET_NAME}/contracts/"
echo "  - Email Notifications: ${SEND_EMAILS}"
if [ "$SEND_EMAILS" = "true" ]; then
    echo "  - Notification Email: ${NOTIFICATION_EMAIL}"
fi
echo ""
echo "📊 Next steps:"
echo "  1. Test the job: gcloud run jobs execute ${JOB_NAME} --region=${REGION}"
echo "  2. View logs: gcloud logging read 'resource.type=cloud_run_job AND resource.labels.job_name=${JOB_NAME}' --limit=50"
echo "  3. Check GCS: gsutil ls gs://${GCS_BUCKET_NAME}/contracts/"
if [ "$SEND_EMAILS" = "true" ]; then
    echo "  4. Verify email delivery to ${NOTIFICATION_EMAIL}"
fi
echo ""