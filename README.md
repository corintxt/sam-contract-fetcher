# Contract Fetcher Cloud Run

Automated daily fetcher for federal contracts from SAM.gov API. Runs as a scheduled Cloud Run Job, fetching contracts and storing them in Google Cloud Storage.

## Features

- 🔄 Runs automatically every day at 6 AM EST
- 📦 Fetches federal contract opportunities from SAM.gov
- ☁️ Serverless deployment using Cloud Run Jobs
- 💾 Stores data in Google Cloud Storage (JSON format)
- 🚀 Simple single-file architecture
- 📊 Built-in logging for monitoring

## Project Structure

```
contract-fetcher-cloud-run/
├── src/
│   └── run_job.py          # Single file with all fetching, processing, and storage logic
├── .env                     # Environment variables (not committed)
├── .env.template            # Template for environment configuration
├── .gitignore               # Git ignore rules
├── Dockerfile               # Container definition
├── README.md                # Documentation
├── deploy.sh                # Automated deployment script
├── requirements.txt         # Python dependencies (3 packages)
└── notes.md                 # Development notes
```

## Requirements

- Python 3.9+
- Google Cloud account with billing enabled
- SAM.gov API key ([get one here](https://open.gsa.gov/api/sam-api/))
- Google Cloud SDK (`gcloud` CLI)

## Setup Instructions

### 1. Clone and Configure

```bash
git clone <repository-url>
cd contract-fetcher-cloud-run

# Copy environment template
cp .env.template .env

# Edit .env with your values
SAM_API_KEY=your_sam_api_key_here
GCS_BUCKET_NAME=your_gcs_bucket_name_here
PROJECT_ID=your_gcp_project_id
REGION=us-central1
LOG_LEVEL=INFO
```

### 2. Create GCS Bucket

```bash
# Create the bucket
gsutil mb -p YOUR_PROJECT_ID -c STANDARD -l us-central1 gs://your_bucket_name

# Verify
gsutil ls
```

### 3. Install Dependencies (for local testing)

```bash
pip install -r requirements.txt
```

### 4. Deploy to Google Cloud

```bash
# Make deploy script executable
chmod +x deploy.sh

# Run deployment (reads config from .env)
./deploy.sh
```

The deployment script will:
- Load configuration from `.env` file (sensitive data never hardcoded)
- Validate all required environment variables
- Enable required GCP APIs
- Build and push Docker container
- Deploy as Cloud Run Job with environment variables
- Configure Cloud Scheduler for daily 6 AM runs
- Set up IAM permissions

**Note:** The `deploy.sh` script is safe to commit to version control as it reads all sensitive data from the `.env` file (which is in `.gitignore`).

## Usage

### Automatic Execution

The job runs automatically every day at **6 AM EST** via Cloud Scheduler. No manual intervention needed!

### Manual Execution

```bash
# Trigger the job manually
gcloud run jobs execute contract-fetcher-job --region=us-central1

# View execution history
gcloud run jobs executions list --job=contract-fetcher-job --region=us-central1

# Check logs
gcloud logging read 'resource.type=cloud_run_job AND resource.labels.job_name=contract-fetcher-job' --limit=50
```

### View Results

```bash
# List uploaded contract files
gsutil ls gs://your_bucket_name/contracts/

# Download latest file
gsutil cp gs://your_bucket_name/contracts/contracts_*.json ./
```

## Monitoring

- **Cloud Run Jobs Console**: https://console.cloud.google.com/run/jobs
- **Cloud Scheduler Console**: https://console.cloud.google.com/cloudscheduler
- **Cloud Storage Console**: https://console.cloud.google.com/storage

## Configuration

The script fetches contracts with these parameters:
- **Date Range**: Previous day's postings
- **Organization**: DHS (code: 070)
- **Notice Types**: Solicitations and Sources Sought
- **Limit**: 200 contracts per fetch

Edit `src/run_job.py` to customize these parameters.

## Troubleshooting

**Job fails to run:**
```bash
# Check job status
gcloud run jobs describe contract-fetcher-job --region=us-central1

# View recent logs
gcloud logging read 'resource.type=cloud_run_job' --limit=50
```

**No files in bucket:**
- Verify bucket name in `.env` matches deployed job
- Check if API returned data (may be normal for date range)
- Review logs for errors

**API rate limits:**
- SAM.gov API has rate limits
- Once limits hit, need to wait until next day

## Development

To test locally:

```bash
# Set environment variables
source .env

# Run the script
python src/run_job.py
```

## License

[ License Here]