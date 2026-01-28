# Contract Fetcher - Technical Documentation

This document explains how the Federal Contract Fetcher application works under the hood. If you're looking for setup and deployment instructions, check the [README](../README.md) instead. This guide is focused on the implementation details and how everything fits together.

## Overview

This is a serverless data pipeline that runs daily on Google Cloud Platform. Every morning at 6 AM EST, it wakes up, fetches the latest federal contract opportunities from SAM.gov's public API, processes the data into a clean format, stores it in both Google Cloud Storage (as JSON) and BigQuery (for querying), and optionally sends an email summary. The whole thing runs as a Docker container via Cloud Run Jobs, triggered by Cloud Scheduler.

The key design principle here is simplicity: it's a single-run job (not a long-running service) that does its work and exits. No databases to manage, no servers to maintain.

## Architecture

The application is organized into four independent Python modules, each with a single responsibility:

```
src/
├── main.py       # Orchestrator - coordinates the whole workflow
├── fetcher.py    # API client - talks to SAM.gov
├── storage.py    # Persistence layer - handles GCS and BigQuery
└── notifier.py   # Email service - sends reports via Mailgun
```

This modular design means you can import and use any module independently. For example, you could import `fetcher.py` in a different project to fetch contracts without using the storage or notification parts.

### The Orchestrator Pattern

The `main.py` module acts as the orchestrator. It doesn't know the details of how to fetch data or send emails - it just knows the sequence of operations and coordinates them. This makes the data pipeline easy to understand: read `main.py` and you'll see exactly what happens on each run.

## Data Flow

Here's what happens when the job runs:

### 1. Configuration & Validation (main.py:59-72)

The job starts by loading environment variables and validating that critical config like `SAM_API_KEY` and `GCS_BUCKET_NAME` are present. If anything is missing, it fails fast with a clear error message.

The `ORG_CODES` environment variable is particularly interesting - it's a comma-separated list of federal organization codes (like "070" for DHS, "075" for HHS). The code parses this into a list and fetches contracts for each organization.

### 2. Fetching Contracts (fetcher.py:15-81)

The `fetch_contracts()` function does the heavy lifting:

- **Default date range**: If you don't specify dates, it defaults to yesterday. This is perfect for a daily job - each morning it fetches contracts posted the previous day.

- **Multi-org fetching**: The function loops through each organization code and makes a separate API call for each. This is necessary because SAM.gov's API only accepts one organization code per request.

- **Deduplication**: Contracts can appear under multiple organizations, so the function tracks `notice_id` values in a set to avoid duplicates.

- **Error handling**: If one organization's API call fails, the job logs a warning and continues with the other organizations. This prevents one bad org code from killing the entire job.

The API request looks like this:
```python
params = {
    "api_key": api_key,
    "organizationCode": org_code,
    "postedFrom": "01/27/2026",      # Yesterday
    "postedTo": "01/27/2026",         # Yesterday
    "active": "true",                 # Only active contracts
    "limit": 200                      # Max per request
}
```

### 3. Processing Contracts (fetcher.py:84-120)

The `process_contracts()` function transforms the raw API response into a flattened, cleaned format that's easier to work with. The SAM.gov API returns deeply nested JSON with inconsistent structures, and this function normalizes it.

Key transformations:
- Extracts nested `officeAddress` fields into flat `office_city` and `office_state`
- Safely navigates the `pointOfContact` array (which might be empty)
- Handles missing/null values gracefully by providing empty strings as defaults
- Strips the response down to just 15 essential fields

The output format matches the BigQuery table schema exactly, which makes the database insert straightforward.

### 4. Local File Save (storage.py:87-104)

Before uploading to the cloud, the job saves the data to a local JSON file. This serves two purposes:
1. It creates a file that can be uploaded to GCS
2. It acts as a temporary backup in case cloud operations fail

The filename is date-based (e.g., `contracts_20260127.json`) for easy identification. The function returns the file size, which gets logged for monitoring.

### 5. Google Cloud Storage Upload (storage.py:14-30)

The `upload_to_gcs()` function is dead simple - it uses the official Google Cloud Storage Python client to upload the local file to a specific path in the bucket. The job stores files under a `contracts/` prefix to keep the bucket organized.

GCS acts as the "source of truth" for raw contract data. If you ever need to rebuild your BigQuery table or analyze historical data, you can pull these JSON files.

### 6. BigQuery Insert (storage.py:33-84)

This is where things get interesting. The `save_to_bigquery()` function doesn't load the JSON file into BigQuery - instead, it streams the contract data directly from memory using the `insert_rows_json()` API.

**Date handling gotcha**: The SAM.gov API returns dates in ISO 8601 format with time information (e.g., `2026-01-27T00:00:00Z`), but BigQuery DATE columns only accept `YYYY-MM-DD`. The function slices the first 10 characters (`:10`) to convert: `posted_date[:10]`.

**Error handling**: BigQuery operations are wrapped in a try-except in `main.py` (lines 114-123). If the insert fails, the job logs a warning but continues. This design choice means a temporary BigQuery issue won't prevent data from being saved to GCS or emails from being sent.

The insert uses the `insert_rows_json` streaming API rather than a load job. This is faster for small datasets (typically < 500 rows per run) and gives immediate feedback if there's a schema mismatch.

### 7. Cleanup (main.py:126-127)

After successfully uploading to both GCS and BigQuery, the job deletes the local JSON file. In the Cloud Run environment, local disk is ephemeral anyway, but cleaning up is good practice.

### 8. Email Notification (notifier.py:12-90)

If emails are enabled, the `send_email_notification()` function generates both HTML and plain text versions of a contract summary email.

The HTML version includes a table with all contracts (not just the top 20 - that was changed at some point based on line 112 comment). Each row has:
- Clickable contract title linking to SAM.gov
- Organization name
- Solicitation number
- Posted date and response deadline
- Office location
- Set-aside type

The function uses Mailgun's API to send the email. It's configured to send from `noreply@{mailgun_domain}` to whatever email is in `NOTIFICATION_EMAIL`.

**Zero-results handling**: The job sends an email even when no contracts are found. This is intentional - it confirms the job ran successfully, rather than leaving you wondering if it failed silently.

## Modules in depth

### main.py - Orchestrator

The orchestrator follows a linear sequence with clear logging at each step. Let's look at some implementation details:

#### Logging Function (main.py:36-40)
```python
def log(message, level="INFO"):
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    print(f"{timestamp} - {level} - {message}")
    sys.stdout.flush()
```

The `sys.stdout.flush()` call is important for Cloud Run. Without it, log messages might be buffered and not appear in Cloud Logging in real-time. This makes debugging much easier.

#### Filename Generation (main.py:43-56)

The `generate_filename()` function handles three cases:
1. Single-day fetch: `contracts_20260127.json`
2. Date range: `contracts_20260127_to_20260130.json`
3. Parse error fallback: `contracts_20260127_143052.json` (with timestamp)

The fallback ensures the job never crashes due to unexpected date formats, though in practice this shouldn't happen since we control the date format.

#### Environment Variable Handling (main.py:22-33)

Organization codes default to "070" (DHS) if not specified. This is a safe default that prevents the job from failing if someone forgets to set `ORG_CODES`.

Email settings use the `os.getenv('SEND_EMAILS', 'false').lower() == 'true'` pattern to treat the env var as a boolean. This means the email feature is opt-in - it won't send emails unless explicitly enabled.

### fetcher.py - API Client

This module handles all interaction with the SAM.gov Opportunities API v2.

#### API Timeout (fetcher.py:59)

The `requests.get()` call includes `timeout=30`, which means the job will fail if SAM.gov doesn't respond within 30 seconds. Without this, the job could hang indefinitely and hit Cloud Run's maximum execution time.

#### Multi-Org Fetching Pattern (fetcher.py:43-80)

The function loops through org codes and accumulates results:
```python
all_opportunities = []
seen_notice_ids = set()

for org_code in org_codes:
    # Make API call for this org
    opportunities = data.get("opportunitiesData", [])

    # Deduplicate by notice_id
    for opp in opportunities:
        notice_id = opp.get("noticeId")
        if notice_id and notice_id not in seen_notice_ids:
            seen_notice_ids.add(notice_id)
            all_opportunities.append(opp)
```

Using a set for deduplication is O(1) lookup time, which is efficient even with hundreds of contracts.

#### Safe Navigation (fetcher.py:98-100)

The processing function uses `or {}` and `or []` patterns to handle null/missing nested objects:
```python
office_address = item.get("officeAddress") or {}
point_of_contact = item.get("pointOfContact") or []
first_contact = point_of_contact[0] if point_of_contact else {}
```

This prevents `TypeError` exceptions when the API returns unexpected null values. It's defensive programming that keeps the job running even with messy data.

### storage.py - Persistence Layer

This module keeps persistence logic separate from business logic. All storage operations go through these functions, making it easy to add new storage backends later (like a database or data warehouse).

#### No Credentials in Code

Notice that neither `storage.Client()` nor `bigquery.Client()` include explicit credentials. The Google Cloud client libraries automatically use Application Default Credentials (ADC), which in Cloud Run means the service account identity.

This is more secure than managing credential files and makes the code portable between local development (using your gcloud credentials) and production (using the Cloud Run service account).

#### BigQuery Schema Mapping (storage.py:54-78)

The function manually maps each field from the processed contract to a BigQuery row. This is verbose but explicit - you can see exactly what data is going where. An alternative would be to rely on BigQuery's auto-detection, but explicit mapping prevents surprises when field names or types don't match.

#### Error Propagation (storage.py:83-84)

If BigQuery returns errors from `insert_rows_json()`, the function raises an exception. The caller (`main.py`) catches this and logs a warning, allowing the job to continue. This is a design decision: GCS is the primary storage, and BigQuery is a nice-to-have for querying.

### notifier.py - Email Service

The email module is completely optional - the job works fine without it. But when enabled, it provides a nice daily summary delivered to your inbox.

#### Mailgun Integration (notifier.py:74-86)

The function uses Mailgun's simple HTTP API rather than an SDK:
```python
mailgun_url = f"https://api.mailgun.net/v3/{mailgun_domain}/messages"
auth = ("api", mailgun_api_key)
data = {
    "from": f"SAM Contract Fetcher <noreply@{mailgun_domain}>",
    "to": to_email,
    "subject": subject,
    "text": text_body,
    "html": html_body
}
response = requests.post(mailgun_url, auth=auth, data=data, timeout=30)
```

HTTP Basic Auth with API key as password is Mailgun's authentication pattern. The timeout prevents the job from hanging on email sends.

#### HTML Table Generation (notifier.py:93-128)

The `_generate_html_table()` function builds an HTML table string with inline CSS. Inline styles are necessary for email - many email clients strip `<style>` tags.

The table is basic but functional. The contract title links directly to SAM.gov using the `ui_link` field, which is convenient for recipients who want to explore opportunities.

## Key Implementation Details

### Environment Variables vs Command-Line Args

The application uses environment variables exclusively for configuration. This is the Cloud Run pattern - when deploying, you pass env vars using `--set-env-vars`. It's cleaner than command-line arguments for containerized applications and integrates well with Kubernetes-style deployments.

### Error Handling Philosophy

The job has two levels of errors:

1. **Fatal errors** (missing API key, GCS bucket unreachable): The job exits with code 1
2. **Recoverable errors** (BigQuery insert fails, email send fails): The job logs a warning and continues

This design ensures data is always saved to GCS (the source of truth) even if downstream operations fail.

### Idempotency

The job is idempotent-ish. Running it twice for the same date will:
- Upload to GCS: Create duplicate files (GCS doesn't prevent overwrites, and filename includes timestamp if run multiple times per day)
- BigQuery insert: Create duplicate rows (no unique constraint on `notice_id`)

In practice this is fine because the Cloud Scheduler job runs once per day at a fixed time. If you need true idempotency, you'd want to:
1. Add a unique constraint on `notice_id` in BigQuery
2. Use `MERGE` or `INSERT IGNORE` statements
3. Or check GCS for existing files before writing

### Memory Efficiency

The entire dataset is loaded into memory (fetched, processed, and formatted) before being written anywhere. For the current scale (typically 50-200 contracts per day, each ~1-2KB), this is fine. The entire job uses < 100MB RAM.

If you needed to fetch thousands of contracts, you'd want to stream data:
1. Fetch in batches
2. Process each batch
3. Write to GCS as a stream
4. Use BigQuery load jobs instead of streaming inserts

### Date Format Handling

Three date formats appear in the code:
- SAM.gov API requires: `MM/DD/YYYY` (e.g., "01/27/2026")
- SAM.gov API returns: ISO 8601 with timezone (e.g., "2026-01-27T00:00:00Z")
- BigQuery DATE columns require: `YYYY-MM-DD` (e.g., "2026-01-27")

The `posted_date[:10]` slice handles the conversion from ISO 8601 to BigQuery DATE format. This works because the first 10 characters of an ISO 8601 datetime are always the date in `YYYY-MM-DD` format.

## Local Testing

The `local/test_main.py` script is a testing harness that uses the same modules as production but with local-friendly behavior:

### Key Differences from Production

1. **Toggleable cloud uploads**: Set `UPLOAD_TO_GCS = False` and `UPLOAD_TO_BIGQUERY = False` to test fetching and processing without touching cloud resources.

2. **Local output directory**: Saves JSON files to `./output/` instead of deleting them. This lets you inspect the data locally.

3. **Custom date/org overrides**: The script includes commented examples (lines 101-104) showing how to test specific dates or organization codes.

4. **Confirmation prompt**: If cloud uploads are enabled, the script asks for confirmation before proceeding. This prevents accidentally uploading test data.

### Running Local Tests

The typical development workflow:
```bash
cd local
python test_main.py
```

This fetches real data from SAM.gov (uses your actual API key) but saves it locally without uploading to GCS or BigQuery. You can inspect the JSON output in the `./output/` directory.

To test the full pipeline including cloud uploads:
```python
UPLOAD_TO_GCS = True
UPLOAD_TO_BIGQUERY = True
```

And run the script - it will prompt for confirmation before uploading.

## Deployment

The `deploy.sh` script automates the entire deployment process:

1. Loads configuration from `.env` (never commits secrets to git)
2. Validates all required environment variables
3. Enables necessary GCP APIs
4. Builds the Docker image using Cloud Build
5. Deploys as a Cloud Run Job
6. Creates a service account for Cloud Scheduler
7. Sets up IAM permissions
8. Creates a Cloud Scheduler job to trigger at 6 AM EST daily

The key insight is that `deploy.sh` itself contains no secrets - it reads everything from `.env`. This means the deployment script can be safely committed to version control.

### Environment Variable Escaping

The deploy script uses `^:^` delimiter syntax for `--set-env-vars`:
```bash
ENV_VARS="^:^SAM_API_KEY=${SAM_API_KEY}:ORG_CODES=${ORG_CODES}:..."
```

This is necessary because `ORG_CODES` contains commas (e.g., "070,075"), and gcloud uses commas as the default delimiter between environment variables. The `^:^` prefix tells gcloud to use `:` as the delimiter instead.

## Monitoring and Observability

All logging goes to stdout, which Cloud Run automatically captures and sends to Cloud Logging. The `log()` function adds timestamps and log levels, making it easy to filter and search logs.

Key log messages to watch for:
- `"Contract Fetcher Job Started"` - Job began execution
- `"API returned X contracts"` - Fetch succeeded
- `"✓ Uploaded to gs://..."` - GCS upload succeeded
- `"✓ Loaded X rows to BigQuery..."` - BigQuery insert succeeded
- `"✓ Email notification sent..."` - Email sent successfully
- `"FATAL ERROR: ..."` - Job crashed

The job returns exit code 0 on success and 1 on fatal errors. Cloud Run tracks execution status based on exit codes.

## Future Enhancements

Some ideas for extending this application:

1. **Contract filtering**: Add logic to filter contracts by NAICS code, set-aside type, or dollar amount before saving
2. **Change detection**: Compare new contracts against previous day's data and only send emails for new/changed contracts
3. **Multiple recipients**: Support a list of email addresses instead of a single recipient
4. **Slack notifications**: Add a Slack notifier module alongside the email notifier
5. **Data retention**: Add logic to delete GCS files older than N days to control storage costs
6. **BigQuery views**: Create SQL views in BigQuery to surface common queries (e.g., contracts by agency, contracts closing soon)

The modular architecture makes these enhancements straightforward - add new modules or extend existing ones without touching the orchestrator.

## Summary

This application is a straightforward data pipeline with a clear separation of concerns. The orchestrator coordinates a sequence of operations (fetch, process, store, notify), and each operation is handled by a dedicated module. The design prioritizes reliability (continues on non-fatal errors), observability (clear logging at each step), and simplicity (no databases or complex state management).

The entire codebase is about 500 lines of Python, but it handles the complete workflow from fetching data from an external API to storing it in a cloud data warehouse and notifying users. That's the power of using managed services (Cloud Run, Cloud Storage, BigQuery) - you get to focus on business logic instead of infrastructure.
