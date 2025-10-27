#!/usr/bin/env python3
"""
SAM.gov federal contract fetcher.
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
    # Uncomment to test specific dates
    # posted_from = "10/24/2025"
    # posted_to = "10/24/2025"
    org_code = "070"  # DHS

    params = {
        "api_key": API_KEY,
        "organizationCode": org_code,
        "postedFrom": posted_from,
        "postedTo": posted_to,
        "active": "true",
        "limit": 200  # Increase limit to get more results
    }

    log(f"Fetching contracts from {posted_from} to {posted_to}")
    response = requests.get(BASE_URL, params=params, timeout=30)

    if response.status_code == 200:
        data = response.json()
        opportunities = data.get("opportunitiesData", [])
        log(f"API returned {len(opportunities)} contracts")
        # Return both the data and the date range for filename
        return opportunities, posted_from, posted_to
    else:
        log(f"API error: {response.status_code} - {response.text}", "ERROR")
        return [], None, None

def process_contracts(raw_data):
    """Process and simplify contract data"""
    processed = []
    
    for item in raw_data:
        # Safe navigation for nested objects
        office_address = item.get("officeAddress") or {}
        point_of_contact = item.get("pointOfContact") or []
        first_contact = point_of_contact[0] if point_of_contact else {}
        
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
            "office_city": office_address.get("city", ""),
            "office_state": office_address.get("state", ""),
            "contact_email": first_contact.get("email", ""),
            "contact_phone": first_contact.get("phone", ""),
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
        raw_contracts, posted_from, posted_to = fetch_contracts()
        
        if not raw_contracts:
            log("No contracts found - this might be normal for the date range")
            return 0
        
        # Step 2: Process contracts
        log(f"Processing {len(raw_contracts)} contracts")
        processed_contracts = process_contracts(raw_contracts)
        
        # Step 3: Save to local file with posting date
        if posted_from and posted_to:
            # Convert date format from MM/DD/YYYY to YYYYMMDD
            try:
                date_obj = datetime.strptime(posted_from, "%m/%d/%Y")
                date_str = date_obj.strftime("%Y%m%d")
                if posted_from != posted_to:
                    date_obj_end = datetime.strptime(posted_to, "%m/%d/%Y")
                    date_str_end = date_obj_end.strftime("%Y%m%d")
                    filename = f"contracts_{date_str}_to_{date_str_end}.json"
                else:
                    filename = f"contracts_{date_str}.json"
            except ValueError:
                # Fallback to fetch timestamp if date parsing fails
                filename = f"contracts_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        else:
            # Fallback to fetch timestamp if no dates available
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
