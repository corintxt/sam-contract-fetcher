#!/usr/bin/env python3
"""
Storage module.
Handles saving contract data to Google Cloud Storage and BigQuery.
"""

import os
import json
from typing import List, Dict
from google.cloud import storage
from google.cloud import bigquery


def upload_to_gcs(
    bucket_name: str,
    source_file: str,
    destination_path: str
) -> None:
    """
    Upload file to Google Cloud Storage.
    
    Args:
        bucket_name: GCS bucket name
        source_file: Local file path to upload
        destination_path: Destination path in GCS bucket
    """
    storage_client = storage.Client()
    bucket = storage_client.bucket(bucket_name)
    blob = bucket.blob(destination_path)
    blob.upload_from_filename(source_file)


def save_to_bigquery(
    contracts: List[Dict],
    project_id: str,
    dataset_id: str = "contracts_data",
    table_id: str = "contracts"
) -> None:
    """
    Save contracts directly to BigQuery.
    
    Args:
        contracts: List of processed contract dictionaries
        project_id: GCP project ID
        dataset_id: BigQuery dataset ID
        table_id: BigQuery table ID
        
    Raises:
        Exception: If BigQuery insert fails
    """
    bq_client = bigquery.Client(project=project_id)
    full_table_id = f"{project_id}.{dataset_id}.{table_id}"
    
    # Prepare data for BigQuery
    rows_to_insert = []
    for contract in contracts:
        # Convert date strings to proper format
        posted_date = contract.get('posted_date', '')[:10] if contract.get('posted_date') else None
        deadline = contract.get('response_deadline', '')[:10] if contract.get('response_deadline') else None
        
        row = {
            "notice_id": contract.get('notice_id', ''),
            "title": contract.get('title', ''),
            "solicitation_number": contract.get('solicitation_number', ''),
            "posted_date": posted_date,
            "response_deadline": deadline,
            "type": contract.get('type', ''),
            "naics_code": contract.get('naics_code', ''),
            "active": contract.get('active', ''),
            "organization": contract.get('organization', ''),
            "office_city": contract.get('office_city', ''),
            "office_state": contract.get('office_state', ''),
            "contact_email": contract.get('contact_email', ''),
            "contact_phone": contract.get('contact_phone', ''),
            "ui_link": contract.get('ui_link', ''),
            "set_aside": contract.get('set_aside', '')
        }
        rows_to_insert.append(row)
    
    # Insert rows into BigQuery
    errors = bq_client.insert_rows_json(full_table_id, rows_to_insert)
    
    if errors:
        raise Exception(f"BigQuery insert failed: {errors}")


def save_to_local_file(
    contracts: List[Dict],
    filename: str
) -> int:
    """
    Save contracts to a local JSON file.
    
    Args:
        contracts: List of contract dictionaries
        filename: Output filename
        
    Returns:
        File size in bytes
    """
    with open(filename, 'w') as f:
        json.dump(contracts, f, indent=2)
    
    return os.path.getsize(filename)
