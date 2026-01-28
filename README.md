# Federal Contract Fetcher (GCloud)

Automated daily fetcher for federal contracts from SAM.gov API. Runs as a scheduled Cloud Run Job, fetching contracts and storing them in Google Cloud Storage and BigQuery.

- Runs automatically every day at 6 AM EST
- Fetches federal contract opportunities from SAM.gov
- Stores data in Google Cloud Storage (JSON format)
- Automatically syncs to BigQuery for analysis
- Email notifications via Mailgun

For a more descriptive explanation see [Documentation](/docs/Documentation.md)

## Project Structure

```
contract-fetcher-cloud-run/
├── src/
│   ├── main.py             # Main orchestrator - coordinates all modules
│   ├── fetcher.py          # Contract fetching and processing
│   ├── storage.py          # GCS and BigQuery storage operations
│   ├── notifier.py         # Email notification via Mailgun
├── local/
│   └── test_local.py       # Local testing script
├── .env                     # Environment variables (not committed)
├── .env.template            # Template for environment configuration
├── .gitignore               # Git ignore rules
├── Dockerfile               # Container definition
├── README.md                # Documentation
├── deploy.sh                # Automated deployment script
└── requirements.txt         # Python dependencies
```

## Modular Architecture

The application is organized into modules:

### `main.py` - Main Orchestrator
Entry point that coordinates all operations

### `fetcher.py` - Contract Fetching
Handles SAM.gov API interactions:
- `fetch_contracts()` - Fetches raw contract data
- `process_contracts()` - Transforms data into simplified format

### `storage.py` - Data Storage
Manages all persistence operations:
- `save_to_local_file()` - Local JSON storage
- `upload_to_gcs()` - Google Cloud Storage backup
- `save_to_bigquery()` - BigQuery data warehouse sync

### `notifier.py` - Email Notifications
Sends email reports via Mailgun:
- `send_email_notification()` - Formatted email with contract summary
- Includes both HTML and plain text versions
- Shows top 20 contracts in table format

## Requirements

- Python 3.9+
- Google Cloud account with billing enabled
- SAM.gov API key ([get one here](https://open.gsa.gov/api/sam-api/))
- Google Cloud SDK (`gcloud` CLI)
- BigQuery dataset and table (see setup below)
- (Optional) Mailgun account for email notifications

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

# Optional: Email notifications
SEND_EMAILS=true
MAILGUN_API_KEY=your_mailgun_api_key
MAILGUN_DOMAIN=your_mailgun_domain
NOTIFICATION_EMAIL=recipient@example.com
```

### 2. Create GCS Bucket

```bash
# Create the bucket
gsutil mb -p YOUR_PROJECT_ID -c STANDARD -l us-central1 gs://your_bucket_name

# Verify
gsutil ls
```

### 3. Create BigQuery Dataset and Table

```bash
# Create dataset
bq mk --dataset --location=us-central1 YOUR_PROJECT_ID:contracts_data

# Create table with schema
bq mk --table \
  YOUR_PROJECT_ID:contracts_data.contracts \
  notice_id:STRING,title:STRING,solicitation_number:STRING,posted_date:DATE,response_deadline:DATE,type:STRING,naics_code:STRING,active:STRING,organization:STRING,office_city:STRING,office_state:STRING,contact_email:STRING,contact_phone:STRING,ui_link:STRING,set_aside:STRING
```

### 4. Install Dependencies (for local testing)

```bash
pip install -r requirements.txt
```

### 5. Deploy to Google Cloud

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
# List uploaded contract files in GCS
gsutil ls gs://your_bucket_name/contracts/

# Download latest file
gsutil cp gs://your_bucket_name/contracts/contracts_*.json ./

# Query BigQuery
bq query --use_legacy_sql=false "
SELECT 
  date(posted_date) as date,
  COUNT(*) as num_contracts,
  COUNT(DISTINCT organization) as num_agencies
FROM \`YOUR_PROJECT_ID.contracts_data.contracts\`
GROUP BY date
ORDER BY date DESC
LIMIT 10
"

# View recent contracts
bq query --use_legacy_sql=false "
SELECT title, organization, posted_date, ui_link
FROM \`YOUR_PROJECT_ID.contracts_data.contracts\`
ORDER BY posted_date DESC
LIMIT 10
"
```

## Monitoring

- **Cloud Run Jobs Console**: https://console.cloud.google.com/run/jobs
- **Cloud Scheduler Console**: https://console.cloud.google.com/cloudscheduler
- **Cloud Storage Console**: https://console.cloud.google.com/storage
- **BigQuery Console**: https://console.cloud.google.com/bigquery

### Check Job Status

```bash
# View recent executions
gcloud run jobs executions list --job=contract-fetcher-job --region=us-central1 --limit=10

# Check logs for errors
gcloud logging read 'resource.type=cloud_run_job AND resource.labels.job_name=contract-fetcher-job' \
  --limit=100 --format="table(timestamp,severity,textPayload)"

# Query BigQuery for row count
bq query --use_legacy_sql=false "SELECT COUNT(*) FROM \`YOUR_PROJECT_ID.contracts_data.contracts\`"
```

## Configuration

The script currently fetches contracts with these parameters:
- **Date Range**: Previous day's postings
- **Organization**: DHS (code: 070)
- **Status**: Active contracts only
- **Limit**: 200 contracts per fetch

Edit `src/fetcher.py` to customize these parameters.

### BigQuery Schema

The BigQuery table uses the following schema:
- `notice_id` (STRING) - Unique notice identifier
- `title` (STRING) - Contract title
- `solicitation_number` (STRING) - Solicitation number
- `posted_date` (DATE) - Date posted
- `response_deadline` (DATE) - Response deadline
- `type` (STRING) - Contract type
- `naics_code` (STRING) - NAICS code
- `active` (STRING) - Active status
- `organization` (STRING) - Full organization path
- `office_city` (STRING) - Office city
- `office_state` (STRING) - Office state
- `contact_email` (STRING) - Contact email
- `contact_phone` (STRING) - Contact phone
- `ui_link` (STRING) - Link to SAM.gov
- `set_aside` (STRING) - Set-aside description

## Development

### Local Testing

```bash
# Test locally with the test script
cd local
python test_local.py

# Or run main script directly
cd ..
python src/main.py
```

### Using Individual Modules

You can import and use modules independently:

```python
from src.fetcher import fetch_contracts, process_contracts
from src.storage import save_to_bigquery

# Fetch and process
raw_contracts, date_from, date_to = fetch_contracts(api_key="YOUR_KEY")
processed = process_contracts(raw_contracts)

# Save to BigQuery
save_to_bigquery(processed, project_id="your-project")
```

## License

Distributed under MIT License