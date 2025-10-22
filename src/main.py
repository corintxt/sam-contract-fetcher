import os
import schedule
import time
import json
from datetime import datetime
from fetcher.contract_fetcher import fetch_contracts
from fetcher.data_processor import process_data
from storage.gcs_handler import upload_to_gcs
from utils.logger import log_info, log_error

def job():
    log_info("Starting the contract fetching job...")
    try:
        # Fetch contracts
        raw_data = fetch_contracts()
        
        if raw_data:
            # Process the data
            processed_data = process_data(raw_data)
            
            # Save to file
            filename = f"contracts_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            with open(filename, 'w') as f:
                json.dump(processed_data, f, indent=2)
            
            # Upload to GCS
            bucket_name = os.getenv('GCS_BUCKET_NAME')
            if bucket_name:
                upload_to_gcs(bucket_name, filename, f"contracts/{filename}")
                os.remove(filename)  # Clean up local file
                log_info(f"Successfully processed {len(processed_data)} contracts")
            else:
                log_error("GCS_BUCKET_NAME environment variable not set")
        else:
            log_info("No contracts fetched")
            
    except Exception as e:
        log_error(f"Error in contract fetching job: {str(e)}")
    
    log_info("Contract fetching job completed.")

if __name__ == "__main__":
    # Schedule the job to run daily at 6 AM
    schedule.every().day.at("06:00").do(job)

    log_info("Scheduler started. Waiting for the scheduled time...")
    
    while True:
        schedule.run_pending()
        time.sleep(1)