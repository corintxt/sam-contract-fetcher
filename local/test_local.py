#!/usr/bin/env python3
"""
Local testing version of contract fetcher.
Saves JSON files locally with option to upload to GCS.
"""

import os
import sys
import json
import requests
import traceback
from datetime import datetime, timedelta
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configuration
API_KEY = os.getenv("SAM_API_KEY")
GCS_BUCKET_NAME = os.getenv("GCS_BUCKET_NAME")
BASE_URL = "https://api.sam.gov/opportunities/v2/search"

# Email configuration
MAILGUN_API_KEY = os.getenv("MAILGUN_API_KEY")
MAILGUN_DOMAIN = os.getenv("MAILGUN_DOMAIN") 
NOTIFICATION_EMAIL = os.getenv("NOTIFICATION_EMAIL")
SEND_EMAILS = os.getenv("SEND_EMAILS", "false").lower() == "true"

# Local testing configuration
UPLOAD_TO_GCS = False  # Set to True to upload to Google Cloud Storage
LOCAL_OUTPUT_DIR = "output"  # Directory to save JSON files locally

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
    
    # Uncomment and modify to test specific dates
    # posted_from = "10/29/2025"
    # posted_to = "10/29/2025"
    
    org_code = "070"  # DHS

    params = {
        "api_key": API_KEY,
        "organizationCode": org_code,
        "postedFrom": posted_from,
        "postedTo": posted_to,
        "active": "true",
        "limit": 200
    }

    log(f"Fetching contracts from {posted_from} to {posted_to}")
    response = requests.get(BASE_URL, params=params, timeout=30)

    if response.status_code == 200:
        data = response.json()
        opportunities = data.get("opportunitiesData", [])
        log(f"API returned {len(opportunities)} contracts")
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

def send_email_notification(contracts, posted_from, posted_to, file_location):
    """Send email notification with contract summary"""
    if not SEND_EMAILS:
        log("Email notifications disabled - set SEND_EMAILS=true to enable")
        return
    
    if not all([MAILGUN_API_KEY, MAILGUN_DOMAIN, NOTIFICATION_EMAIL]):
        log("Email configuration incomplete - skipping notification", "WARNING")
        return
    
    try:
        # Create email content
        contract_count = len(contracts)
        subject = f"DHS Contract Report - {contract_count} contracts found ({posted_from})"
        
        # Generate HTML table of contracts
        contracts_table = ""
        if contracts:
            contracts_table = "<table border='1' cellpadding='5' cellspacing='0' style='border-collapse: collapse; width: 100%;'>"
            contracts_table += """
            <tr style='background-color: #f2f2f2;'>
                <th>Title</th>
                <th>Solicitation #</th>
                <th>Posted Date</th>
                <th>Deadline</th>
                <th>Type</th>
                <th>NAICS</th>
                <th>Office Location</th>
                <th>Set Aside</th>
            </tr>
            """
            
            for contract in contracts[:20]:  # Limit to first 20 for email
                contracts_table += f"""
                <tr>
                    <td><a href="{contract.get('ui_link', '#')}" target="_blank">{contract.get('title', 'N/A')}</a></td>
                    <td>{contract.get('solicitation_number', 'N/A')}</td>
                    <td>{contract.get('posted_date', 'N/A')}</td>
                    <td>{contract.get('response_deadline', 'N/A')}</td>
                    <td>{contract.get('type', 'N/A')}</td>
                    <td>{contract.get('naics_code', 'N/A')}</td>
                    <td>{contract.get('office_city', 'N/A')}, {contract.get('office_state', 'N/A')}</td>
                    <td>{contract.get('set_aside', 'N/A')}</td>
                </tr>
                """
            
            contracts_table += "</table>"
            
            if len(contracts) > 20:
                contracts_table += f"<p><em>... and {len(contracts) - 20} more contracts. Full data available in the JSON file.</em></p>"
        else:
            contracts_table = "<p>No contracts found for this date range.</p>"
        
        # HTML email body
        html_body = f"""
        <html>
        <body>
            <h2>DHS Contract Fetcher Daily Report</h2>
            <p><strong>Date Range:</strong> {posted_from} to {posted_to}</p>
            <p><strong>Total Contracts Found:</strong> {contract_count}</p>
            <p><strong>Data Location:</strong> {file_location}</p>
            
            <h3>Contract Summary:</h3>
            {contracts_table}
            
            <hr>
            <p><small>This is an automated report from the DHS Contract Fetcher service.</small></p>
        </body>
        </html>
        """
        
        # Plain text version
        text_body = f"""
DHS Contract Fetcher Daily Report

Date Range: {posted_from} to {posted_to}
Total Contracts Found: {contract_count}
Data Location: {file_location}

Contract Details:
"""
        
        for i, contract in enumerate(contracts[:10], 1):  # First 10 for text version
            text_body += f"""
{i}. {contract.get('title', 'N/A')}
   Solicitation: {contract.get('solicitation_number', 'N/A')}
   Posted: {contract.get('posted_date', 'N/A')}
   Deadline: {contract.get('response_deadline', 'N/A')}
   Link: {contract.get('ui_link', 'N/A')}
"""
        
        if len(contracts) > 10:
            text_body += f"\n... and {len(contracts) - 10} more contracts in the full data file."
        
        # Send email via Mailgun
        mailgun_url = f"https://api.mailgun.net/v3/{MAILGUN_DOMAIN}/messages"
        auth = ("api", MAILGUN_API_KEY)
        
        data = {
            "from": f"DHS Contract Fetcher <noreply@{MAILGUN_DOMAIN}>",
            "to": NOTIFICATION_EMAIL,
            "subject": subject,
            "text": text_body,
            "html": html_body
        }
        
        response = requests.post(mailgun_url, auth=auth, data=data, timeout=30)
        
        if response.status_code == 200:
            log(f"✓ Email notification sent successfully to {NOTIFICATION_EMAIL}")
        else:
            log(f"Failed to send email: {response.status_code} - {response.text}", "WARNING")
            
    except Exception as e:
        log(f"Error sending email notification: {str(e)}", "WARNING")

def upload_to_gcs(bucket_name, source_file, destination_path):
    """Upload file to Google Cloud Storage"""
    try:
        from google.cloud import storage
        storage_client = storage.Client()
        bucket = storage_client.bucket(bucket_name)
        blob = bucket.blob(destination_path)
        blob.upload_from_filename(source_file)
        log(f"Uploaded to gs://{bucket_name}/{destination_path}")
        return True
    except ImportError:
        log("google-cloud-storage not installed. Install with: pip install google-cloud-storage", "ERROR")
        return False
    except Exception as e:
        log(f"GCS upload failed: {str(e)}", "ERROR")
        return False

def ensure_output_dir():
    """Create output directory if it doesn't exist"""
    if not os.path.exists(LOCAL_OUTPUT_DIR):
        os.makedirs(LOCAL_OUTPUT_DIR)
        log(f"Created output directory: {LOCAL_OUTPUT_DIR}")

def run():
    """Main execution function"""
    log("=" * 60)
    log("Contract Fetcher - Local Testing Version")
    log(f"Upload to GCS: {'ENABLED' if UPLOAD_TO_GCS else 'DISABLED'}")
    log(f"Local output directory: {LOCAL_OUTPUT_DIR}")
    log("=" * 60)
    
    # Validate configuration
    if not API_KEY:
        log("ERROR: SAM_API_KEY not set in .env file", "ERROR")
        return 1
    
    if UPLOAD_TO_GCS and not GCS_BUCKET_NAME:
        log("ERROR: GCS_BUCKET_NAME not set in .env file (required when UPLOAD_TO_GCS=True)", "ERROR")
        return 1
    
    try:
        # Step 1: Ensure output directory exists
        ensure_output_dir()
        
        # Step 2: Fetch contracts
        raw_contracts, posted_from, posted_to = fetch_contracts()
        
        if not raw_contracts:
            log("No contracts found - this might be normal for the date range")
            return 0
        
        # Step 3: Process contracts
        log(f"Processing {len(raw_contracts)} contracts")
        processed_contracts = process_contracts(raw_contracts)
        
        # Step 4: Generate filename based on posting date
        if posted_from and posted_to:
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
                filename = f"contracts_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        else:
            filename = f"contracts_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        
        # Step 5: Save to local file
        local_filepath = os.path.join(LOCAL_OUTPUT_DIR, filename)
        with open(local_filepath, 'w') as f:
            json.dump(processed_contracts, f, indent=2)
        
        file_size = os.path.getsize(local_filepath)
        log(f"Saved to {local_filepath} ({file_size:,} bytes)")
        
        # Step 6: Upload to GCS (if enabled)
        if UPLOAD_TO_GCS:
            log("Uploading to Google Cloud Storage...")
            destination = f"contracts/{filename}"
            success = upload_to_gcs(GCS_BUCKET_NAME, local_filepath, destination)
            if success:
                log(f"✓ Data saved to gs://{GCS_BUCKET_NAME}/{destination}")
            else:
                log("✗ GCS upload failed, but local file saved successfully")
        else:
            log("GCS upload disabled - file saved locally only")
        
        # Step 7: Send email notification (if configured)
        file_location = local_filepath
        if UPLOAD_TO_GCS and GCS_BUCKET_NAME:
            file_location = f"gs://{GCS_BUCKET_NAME}/contracts/{filename}"
        send_email_notification(processed_contracts, posted_from, posted_to, file_location)
        
        # Success summary
        log("=" * 60)
        log(f"✓ Successfully processed {len(processed_contracts)} contracts")
        log(f"✓ Local file: {local_filepath}")
        if UPLOAD_TO_GCS and GCS_BUCKET_NAME:
            log(f"✓ GCS location: gs://{GCS_BUCKET_NAME}/contracts/{filename}")
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
    print(f"  LOCAL_OUTPUT_DIR = '{LOCAL_OUTPUT_DIR}'")
    print(f"  SAM_API_KEY = {'SET' if API_KEY else 'NOT SET'}")
    print(f"  GCS_BUCKET_NAME = {GCS_BUCKET_NAME or 'NOT SET'}")
    print()
    
    # Ask for confirmation if GCS upload is enabled
    if UPLOAD_TO_GCS:
        response = input("GCS upload is ENABLED. Continue? (y/N): ")
        if response.lower() not in ['y', 'yes']:
            print("Cancelled.")
            sys.exit(0)
    
    exit_code = run()
    sys.exit(exit_code)