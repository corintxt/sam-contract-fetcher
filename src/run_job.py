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

def send_email_notification(contracts, filename, success=True, error_message=None):
    """Send email notification via Mailgun"""
    
    # Check if emails are enabled
    if not os.getenv('SEND_EMAILS', 'false').lower() == 'true':
        log("Email notifications disabled")
        return True
    
    mailgun_api_key = os.getenv('MAILGUN_API_KEY')
    mailgun_domain = os.getenv('MAILGUN_DOMAIN')
    to_email = os.getenv('NOTIFICATION_EMAIL')
    
    if not all([mailgun_api_key, mailgun_domain, to_email]):
        log("Email configuration incomplete - skipping email", "WARNING")
        return True
    
    try:
        from_email = f"Contract Monitor <monitor@{mailgun_domain}>"
        
        if success:
            # Success email with contract summary
            contract_count = len(contracts)
            
            # Get top 5 contracts by title length (as a proxy for importance)
            top_contracts = sorted(contracts, key=lambda x: len(x.get('title', '')), reverse=True)[:5]
            
            subject = f"Federal Contracts Report - {contract_count} contracts found"
            
            # Create HTML email content
            html_content = f"""
            <html>
            <body style="font-family: Arial, sans-serif; margin: 20px;">
                <h2>📊 Federal Contracts Daily Report</h2>
                <p><strong>Date:</strong> {datetime.now().strftime('%B %d, %Y')}</p>
                
                <div style="background-color: #f0f8ff; padding: 15px; border-radius: 8px; margin: 20px 0;">
                    <h3>📈 Summary</h3>
                    <ul>
                        <li><strong>Contracts Found:</strong> {contract_count}</li>
                        <li><strong>File:</strong> {filename}</li>
                    </ul>
                </div>
            """
            
            if top_contracts:
                html_content += """
                <h3>🏆 Top 5 Contracts</h3>
                <table style="width: 100%; border-collapse: collapse; margin: 10px 0;">
                    <thead>
                        <tr style="background-color: #4CAF50; color: white;">
                            <th style="padding: 12px; text-align: left; border: 1px solid #ddd;">Organization</th>
                            <th style="padding: 12px; text-align: left; border: 1px solid #ddd;">Title</th>
                            <th style="padding: 12px; text-align: left; border: 1px solid #ddd;">Posted Date</th>
                        </tr>
                    </thead>
                    <tbody>
                """
                
                for i, contract in enumerate(top_contracts):
                    bg_color = "#f9f9f9" if i % 2 == 0 else "white"
                    organization = contract.get('organization', 'N/A')[:50]
                    title = contract.get('title', 'N/A')[:80] + ('...' if len(contract.get('title', '')) > 80 else '')
                    posted_date = contract.get('posted_date', 'N/A')
                    
                    html_content += f"""
                        <tr style="background-color: {bg_color};">
                            <td style="padding: 10px; border: 1px solid #ddd;">{organization}</td>
                            <td style="padding: 10px; border: 1px solid #ddd;">{title}</td>
                            <td style="padding: 10px; border: 1px solid #ddd;">{posted_date}</td>
                        </tr>
                    """
                
                html_content += """
                    </tbody>
                </table>
                """
            
            html_content += """
                <p style="margin-top: 30px; color: #666; font-size: 14px;">
                    This is an automated report from your Federal Contract Monitor.<br>
                    Data is stored in Google Cloud Storage for further analysis.
                </p>
            </body>
            </html>
            """
            
            # Plain text version
            text_content = f"""
Federal Contracts Daily Report - {datetime.now().strftime('%B %d, %Y')}

Summary:
- Contracts Found: {contract_count}
- File: {filename}

This is an automated report from your Federal Contract Monitor.
            """
        
        else:
            # Error email
            subject = "Federal Contracts Report - ERROR"
            html_content = f"""
            <html>
            <body style="font-family: Arial, sans-serif; margin: 20px;">
                <h2>❌ Federal Contracts Report - Error</h2>
                <p><strong>Date:</strong> {datetime.now().strftime('%B %d, %Y')}</p>
                
                <div style="background-color: #ffebee; padding: 15px; border-radius: 8px; margin: 20px 0; border-left: 4px solid #f44336;">
                    <h3>Error Details</h3>
                    <p><strong>Error:</strong> {error_message}</p>
                </div>
                
                <p style="color: #666;">Please check the Cloud Run logs for more details.</p>
            </body>
            </html>
            """
            
            text_content = f"""
Federal Contracts Report - ERROR

Date: {datetime.now().strftime('%B %d, %Y')}
Error: {error_message}

Please check the Cloud Run logs for more details.
            """
        
        # Send email via Mailgun
        url = f"https://api.mailgun.net/v3/{mailgun_domain}/messages"
        
        data = {
            "from": from_email,
            "to": to_email,
            "subject": subject,
            "text": text_content,
            "html": html_content
        }
        
        response = requests.post(
            url,
            auth=("api", mailgun_api_key),
            data=data,
            timeout=30
        )
        
        response.raise_for_status()
        log(f"Email sent successfully! Message ID: {response.json()['id']}")
        return True
        
    except Exception as e:
        log(f"Failed to send email: {str(e)}", "ERROR")
        return False

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
        
        # Step 6: Send email notification (if configured)
        send_email_notification(processed_contracts, posted_from, posted_to, f"gs://{GCS_BUCKET_NAME}/{destination}")
        
        return 0
        
    except Exception as e:
        log(f"FATAL ERROR: {str(e)}", "ERROR")
        log(traceback.format_exc(), "ERROR")
        return 1

if __name__ == "__main__":
    exit_code = run()
    sys.exit(exit_code)
