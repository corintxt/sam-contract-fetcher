#!/usr/bin/env python3
"""
Local testing version of main orchestrator.
Uses the same modules as cloud version but with local testing options.
"""

import os
import sys
import traceback
from datetime import datetime

# Add src directory to path to import modules
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from dotenv import load_dotenv
from fetcher import fetch_contracts, process_contracts
from storage import save_to_local_file, upload_to_gcs, save_to_bigquery
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

# Local testing configuration
UPLOAD_TO_GCS = False  # Set to True to upload to Google Cloud Storage
UPLOAD_TO_BIGQUERY = False  # Set to True to upload to BigQuery
LOCAL_OUTPUT_DIR = "output"  # Directory to save JSON files locally


def log(message, level="INFO"):
    """Simple logging"""
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    print(f"{timestamp} - {level} - {message}")
    sys.stdout.flush()


def ensure_output_dir():
    """Create output directory if it doesn't exist"""
    if not os.path.exists(LOCAL_OUTPUT_DIR):
        os.makedirs(LOCAL_OUTPUT_DIR)
        log(f"Created output directory: {LOCAL_OUTPUT_DIR}")


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
    log("Contract Fetcher - Local Testing Version")
    log(f"Upload to GCS: {'ENABLED' if UPLOAD_TO_GCS else 'DISABLED'}")
    log(f"Upload to BigQuery: {'ENABLED' if UPLOAD_TO_BIGQUERY else 'DISABLED'}")
    log(f"Local output directory: {LOCAL_OUTPUT_DIR}")
    log("=" * 60)
    
    # Validate configuration
    if not API_KEY:
        log("ERROR: SAM_API_KEY not set in .env file", "ERROR")
        return 1
    
    if UPLOAD_TO_GCS and not GCS_BUCKET_NAME:
        log("ERROR: GCS_BUCKET_NAME not set (required when UPLOAD_TO_GCS=True)", "ERROR")
        return 1
    
    if UPLOAD_TO_BIGQUERY and not GCP_PROJECT_ID:
        log("ERROR: PROJECT_ID not set (required when UPLOAD_TO_BIGQUERY=True)", "ERROR")
        return 1
    
    try:
        # Step 1: Ensure output directory exists
        ensure_output_dir()
        
        # Step 2: Fetch contracts
        log("Fetching contracts from SAM.gov API...")
        # To test specific dates, uncomment and modify:
        # raw_contracts, posted_from, posted_to = fetch_contracts(API_KEY, posted_from="10/25/2025", posted_to="10/25/2025")
        raw_contracts, posted_from, posted_to = fetch_contracts(API_KEY)
        log(f"API returned {len(raw_contracts)} contracts")
        
        if not raw_contracts:
            log("No contracts found - this might be normal for the date range")
            # Send notification even with 0 contracts if configured
            if SEND_EMAILS:
                send_email_notification(
                    [], posted_from, posted_to,
                    "No data - no contracts found",
                    MAILGUN_API_KEY, MAILGUN_DOMAIN, NOTIFICATION_EMAIL,
                    enabled=True
                )
                log("Sent notification for zero contracts")
            return 0
        
        # Step 3: Process contracts
        log(f"Processing {len(raw_contracts)} contracts...")
        processed_contracts = process_contracts(raw_contracts)
        
        # Step 4: Generate filename
        filename = generate_filename(posted_from, posted_to)
        local_filepath = os.path.join(LOCAL_OUTPUT_DIR, filename)
        
        # Step 5: Save to local file
        file_size = save_to_local_file(processed_contracts, local_filepath)
        log(f"Saved to {local_filepath} ({file_size:,} bytes)")
        
        # Step 6: Upload to GCS (if enabled)
        gcs_location = None
        if UPLOAD_TO_GCS:
            log("Uploading to Google Cloud Storage...")
            destination = f"contracts/{filename}"
            try:
                upload_to_gcs(GCS_BUCKET_NAME, local_filepath, destination)
                gcs_location = f"gs://{GCS_BUCKET_NAME}/{destination}"
                log(f"✓ Uploaded to {gcs_location}")
            except Exception as e:
                log(f"GCS upload failed: {str(e)}", "WARNING")
        else:
            log("GCS upload disabled")
        
        # Step 7: Save to BigQuery (if enabled)
        if UPLOAD_TO_BIGQUERY:
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
                log(f"BigQuery upload failed: {str(bq_error)}", "WARNING")
        else:
            log("BigQuery upload disabled")
        
        # Step 8: Send email notification (if configured)
        if SEND_EMAILS:
            log("Sending email notification...")
            file_location = gcs_location or local_filepath
            success = send_email_notification(
                processed_contracts,
                posted_from,
                posted_to,
                file_location,
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
        log(f"✓ Local file: {local_filepath}")
        if gcs_location:
            log(f"✓ GCS location: {gcs_location}")
        log("=" * 60)
        
        return 0
        
    except Exception as e:
        log(f"FATAL ERROR: {str(e)}", "ERROR")
        log(traceback.format_exc(), "ERROR")
        return 1


if __name__ == "__main__":
    print(f"Contract Fetcher - Local Testing Version")
    print(f"Configuration:")
    print(f"  UPLOAD_TO_GCS = {UPLOAD_TO_GCS}")
    print(f"  UPLOAD_TO_BIGQUERY = {UPLOAD_TO_BIGQUERY}")
    print(f"  LOCAL_OUTPUT_DIR = '{LOCAL_OUTPUT_DIR}'")
    print(f"  SAM_API_KEY = {'SET' if API_KEY else 'NOT SET'}")
    print(f"  GCS_BUCKET_NAME = {GCS_BUCKET_NAME or 'NOT SET'}")
    print(f"  PROJECT_ID = {GCP_PROJECT_ID or 'NOT SET'}")
    print()
    
    # Ask for confirmation if GCS or BigQuery upload is enabled
    if UPLOAD_TO_GCS or UPLOAD_TO_BIGQUERY:
        uploads_enabled = []
        if UPLOAD_TO_GCS:
            uploads_enabled.append("GCS")
        if UPLOAD_TO_BIGQUERY:
            uploads_enabled.append("BigQuery")
        
        response = input(f"{', '.join(uploads_enabled)} upload is ENABLED. Continue? (y/N): ")
        if response.lower() not in ['y', 'yes']:
            print("Cancelled.")
            sys.exit(0)
    
    exit_code = run()
    sys.exit(exit_code)
