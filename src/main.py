#!/usr/bin/env python3
"""
Main job orchestrator.
Coordinates fetching, storing, and notifying for contract data.
"""

import os
import sys
import traceback
from datetime import datetime
from dotenv import load_dotenv

# Import our modules
from fetcher import fetch_contracts, process_contracts
from storage import upload_to_gcs, save_to_bigquery, save_to_local_file
from notifier import send_email_notification

# Load environment variables
load_dotenv()

# Configuration
API_KEY = os.getenv("SAM_API_KEY")
GCS_BUCKET_NAME = os.getenv("GCS_BUCKET_NAME")
GCP_PROJECT_ID = os.getenv("PROJECT_ID")
BIGQUERY_DATASET = "contracts_data"
BIGQUERY_TABLE = "contracts"

# Email configuration
SEND_EMAILS = os.getenv('SEND_EMAILS', 'false').lower() == 'true'
MAILGUN_API_KEY = os.getenv('MAILGUN_API_KEY')
MAILGUN_DOMAIN = os.getenv('MAILGUN_DOMAIN')
NOTIFICATION_EMAIL = os.getenv('NOTIFICATION_EMAIL')


def log(message, level="INFO"):
    """Simple logging"""
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    print(f"{timestamp} - {level} - {message}")
    sys.stdout.flush()


def generate_filename(posted_from: str, posted_to: str) -> str:
    """Generate filename based on date range."""
    try:
        date_obj = datetime.strptime(posted_from, "%m/%d/%Y")
        date_str = date_obj.strftime("%Y%m%d")
        if posted_from != posted_to:
            date_obj_end = datetime.strptime(posted_to, "%m/%d/%Y")
            date_str_end = date_obj_end.strftime("%Y%m%d")
            return f"contracts_{date_str}_to_{date_str_end}.json"
        else:
            return f"contracts_{date_str}.json"
    except ValueError:
        # Fallback to timestamp if date parsing fails
        return f"contracts_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"


def run():
    """Main execution function"""
    log("=" * 60)
    log("Contract Fetcher Job Started")
    log("=" * 60)
    
    # Validate configuration
    if not API_KEY:
        log("ERROR: SAM_API_KEY not set", "ERROR")
        return 1
    
    if not GCS_BUCKET_NAME:
        log("ERROR: GCS_BUCKET_NAME not set", "ERROR")
        return 1
    
    try:
        # Step 1: Fetch contracts
        log("Fetching contracts from SAM.gov API...")
        raw_contracts, posted_from, posted_to = fetch_contracts(API_KEY)
        log(f"API returned {len(raw_contracts)} contracts")
        
        if not raw_contracts:
            log("No contracts found - this might be normal for the date range")
            # Send notification even with 0 contracts so you know the job ran
            if SEND_EMAILS:
                send_email_notification(
                    [], posted_from, posted_to,
                    "No data - no contracts found",
                    MAILGUN_API_KEY, MAILGUN_DOMAIN, NOTIFICATION_EMAIL,
                    enabled=True
                )
                log("Sent notification for zero contracts")
            return 0
        
        # Step 2: Process contracts
        log(f"Processing {len(raw_contracts)} contracts...")
        processed_contracts = process_contracts(raw_contracts)
        
        # Step 3: Save to local file
        filename = generate_filename(posted_from, posted_to)
        file_size = save_to_local_file(processed_contracts, filename)
        log(f"Saved to {filename} ({file_size:,} bytes)")
        
        # Step 4: Upload to GCS
        log("Uploading to Google Cloud Storage...")
        destination = f"contracts/{filename}"
        upload_to_gcs(GCS_BUCKET_NAME, filename, destination)
        log(f"✓ Uploaded to gs://{GCS_BUCKET_NAME}/{destination}")
        
        # Step 5: Save to BigQuery (non-blocking - continue on failure)
        log("Saving to BigQuery...")
        try:
            save_to_bigquery(
                processed_contracts,
                GCP_PROJECT_ID,
                BIGQUERY_DATASET,
                BIGQUERY_TABLE
            )
            log(f"✓ Loaded {len(processed_contracts)} rows to BigQuery table {GCP_PROJECT_ID}.{BIGQUERY_DATASET}.{BIGQUERY_TABLE}")
        except Exception as bq_error:
            log(f"BigQuery upload failed but continuing: {str(bq_error)}", "WARNING")
        
        # Step 6: Cleanup local file
        os.remove(filename)
        log(f"Removed local file {filename}")
        
        # Step 7: Send email notification (if configured)
        if SEND_EMAILS:
            log("Sending email notification...")
            success = send_email_notification(
                processed_contracts,
                posted_from,
                posted_to,
                f"gs://{GCS_BUCKET_NAME}/{destination}",
                MAILGUN_API_KEY,
                MAILGUN_DOMAIN,
                NOTIFICATION_EMAIL,
                enabled=True
            )
            if success:
                log(f"✓ Email notification sent to {NOTIFICATION_EMAIL}")
            else:
                log("Email notification failed", "WARNING")
        else:
            log("Email notifications disabled")
        
        # Success summary
        log("=" * 60)
        log(f"✓ Successfully processed {len(processed_contracts)} contracts")
        log(f"✓ Data saved to gs://{GCS_BUCKET_NAME}/{destination}")
        log("=" * 60)
        
        return 0
        
    except Exception as e:
        log(f"FATAL ERROR: {str(e)}", "ERROR")
        log(traceback.format_exc(), "ERROR")
        return 1


if __name__ == "__main__":
    exit_code = run()
    sys.exit(exit_code)
