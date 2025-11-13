# Local Testing Guide

## Overview

The local testing script (`test_main.py`) uses the same modular architecture as the cloud version but with options for local-only testing. You can selectively enable/disable GCS upload, BigQuery sync, and email notifications.

## Quick Start

```bash
# Run with local-only output (no cloud uploads)
python local/test_main.py

# Or use the legacy monolithic script
python local/test_local.py
```

## Configuration

Edit these variables at the top of `test_main.py`:

```python
UPLOAD_TO_GCS = False       # Set to True to upload to Google Cloud Storage
UPLOAD_TO_BIGQUERY = False  # Set to True to sync to BigQuery
LOCAL_OUTPUT_DIR = "output"  # Directory to save JSON files locally
```

Email notifications are controlled by environment variables in `.env`:
```bash
SEND_EMAILS=true
MAILGUN_API_KEY=your_key
MAILGUN_DOMAIN=your_domain
NOTIFICATION_EMAIL=recipient@example.com
```

## Test Specific Dates

In `test_main.py`, uncomment and modify line 103:

```python
# Change from:
raw_contracts, posted_from, posted_to = fetch_contracts(API_KEY)

# To:
raw_contracts, posted_from, posted_to = fetch_contracts(API_KEY, posted_from="10/25/2025", posted_to="10/25/2025")
```

## Output

- **Local files**: Saved to `output/` directory
- **GCS files**: Uploaded to `gs://your-bucket/contracts/` (if enabled)
- **BigQuery**: Records inserted into `contracts_data.contracts` table (if enabled)
- **Email**: Sent via Mailgun (if enabled)
- **Filenames**: Based on contract posting date (e.g., `contracts_20251113.json`)

## Testing Scenarios

### Scenario 1: Local Only (Default)
```python
UPLOAD_TO_GCS = False
UPLOAD_TO_BIGQUERY = False
SEND_EMAILS = false  # in .env
```
- Fetches contracts and saves to local `output/` directory
- No cloud resources used
- Fastest for testing data fetching

### Scenario 2: With GCS Backup
```python
UPLOAD_TO_GCS = True
UPLOAD_TO_BIGQUERY = False
```
- Saves locally AND uploads to Cloud Storage
- Good for testing GCS integration
- Requires `GCS_BUCKET_NAME` in `.env`

### Scenario 3: Full Pipeline (Production-like)
```python
UPLOAD_TO_GCS = True
UPLOAD_TO_BIGQUERY = True
SEND_EMAILS = true  # in .env
```
- Complete pipeline: fetch → save → GCS → BigQuery → email
- Tests entire workflow locally
- Requires all credentials configured

### Scenario 4: BigQuery Only
```python
UPLOAD_TO_GCS = False
UPLOAD_TO_BIGQUERY = True
```
- Saves locally and syncs to BigQuery
- Skips GCS backup
- Good for testing BigQuery schema

## Requirements

**Always required:**
- `.env` file with `SAM_API_KEY`
- Dependencies: `pip install -r requirements.txt`

**Conditionally required:**
- `GCS_BUCKET_NAME` (if `UPLOAD_TO_GCS = True`)
- `PROJECT_ID` (if `UPLOAD_TO_BIGQUERY = True`)
- Mailgun credentials (if `SEND_EMAILS=true`)

## Differences from Cloud Version

| Feature | Cloud (`main.py`) | Local (`test_main.py`) |
|---------|-------------------|------------------------|
| GCS Upload | Always | Optional (default: OFF) |
| BigQuery | Always | Optional (default: OFF) |
| Email | Configurable | Configurable |
| Output Location | Temp file, deleted | `output/` directory, kept |
| Error on Missing | Fails if GCS unavailable | Continues without cloud |

## Troubleshooting

**Import errors:**
```bash
# Make sure you're in the project root directory
cd /path/to/contract-fetcher-cloud-run
python local/test_main.py
```

**GCS authentication:**
```bash
# Set up application default credentials
gcloud auth application-default login
```

**Module not found:**
```bash
# Ensure src modules exist
ls src/fetcher.py src/storage.py src/notifier.py
```