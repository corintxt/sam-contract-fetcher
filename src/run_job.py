#!/usr/bin/env python3
"""
Simplified contract fetcher - runs once and exits.
Triggered by Cloud Scheduler via Cloud Run Jobs.
"""

import os
import sys
import json
import requests
import traceback
from datetime import datetime, timedelta
from dotenv import load_dotenv
from google.cloud import storage

# Load environment variables
load_dotenv()

# Configuration
API_KEY = os.getenv("SAM_API_KEY")
GCS_BUCKET_NAME = os.getenv("GCS_BUCKET_NAME")
BASE_URL = "https://api.sam.gov/opportunities/v2/search"

def log(message, level="INFO"):
    """Simple logging"""
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    print(f"{timestamp} - {level} - {message}")
    sys.stdout.flush()

def fetch_contracts():
    """Fetch contracts from SAM.gov API"""
    yesterday = datetime.now() - timedelta(days=1)
    posted_from = yesterday.strftime("%m/%d/%Y")
    posted_to = yesterday.strftime("%m/%d/%Y")

    params = {
        "api_key": API_KEY,
        "postedFrom": posted_from,
        "postedTo": posted_to,
        "active": "true",
        "limit": 1000
    }

    log(f"Fetching contracts from {posted_from} to {posted_to}")
    response = requests.get(BASE_URL, params=params, timeout=30)

    if response.status_code == 200:
        data = response.json()
        opportunities = data.get("opportunitiesData", [])
        log(f"API returned {len(opportunities)} contracts")
        return opportunities
    else:
        log(f"API error: {response.status_code} - {response.text}", "ERROR")
        return []

def process_contracts(raw_data):
    """Process and simplify contract data"""
    processed = []
    
    for item in raw_data:
        processed.append({
            "notice_id": item.get("noticeId", ""),
            "title": item.get("title", ""),
            "solicitation_number": item.get("solicitationNumber", ""),
            "posted_date": item.get("postedDate", ""),
            "response_deadline": item.get("responseDeadLine", ""),
            "type": item.get("type", ""),
            "naics_code": item.get("naicsCode", ""),
            "active": item.get("active", ""),
            "organization": item.get("fullParentPathName", ""),
            "office_city": item.get("officeAddress", {}).get("city", ""),
            "office_state": item.get("officeAddress", {}).get("state", ""),
            "contact_email": item.get("pointOfContact", [{}])[0].get("email", "") if item.get("pointOfContact") else "",
            "contact_phone": item.get("pointOfContact", [{}])[0].get("phone", "") if item.get("pointOfContact") else "",
            "ui_link": item.get("uiLink", ""),
            "set_aside": item.get("typeOfSetAsideDescription", "")
        })
    
    return processed

def upload_to_gcs(bucket_name, source_file, destination_path):
    """Upload file to Google Cloud Storage"""
    storage_client = storage.Client()
    bucket = storage_client.bucket(bucket_name)
    blob = bucket.blob(destination_path)
    blob.upload_from_filename(source_file)
    log(f"Uploaded to gs://{bucket_name}/{destination_path}")

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
        raw_contracts = fetch_contracts()
        
        if not raw_contracts:
            log("No contracts found - this might be normal for the date range")
            return 0
        
        # Step 2: Process contracts
        log(f"Processing {len(raw_contracts)} contracts")
        processed_contracts = process_contracts(raw_contracts)
        
        # Step 3: Save to local file
        filename = f"contracts_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(filename, 'w') as f:
            json.dump(processed_contracts, f, indent=2)
        
        file_size = os.path.getsize(filename)
        log(f"Saved to {filename} ({file_size:,} bytes)")
        
        # Step 4: Upload to GCS
        destination = f"contracts/{filename}"
        upload_to_gcs(GCS_BUCKET_NAME, filename, destination)
        
        # Step 5: Cleanup
        os.remove(filename)
        log(f"Removed local file {filename}")
        
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
