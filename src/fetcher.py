#!/usr/bin/env python3
"""
Contract fetcher module.
Handles fetching and processing contract data from SAM.gov API.
"""

import os
import requests
from datetime import datetime, timedelta
from typing import List, Dict, Tuple, Optional

BASE_URL = "https://api.sam.gov/opportunities/v2/search"


def fetch_contracts(
    api_key: str,
    posted_from: Optional[str] = None,
    posted_to: Optional[str] = None,
    org_code: str = "070"
) -> Tuple[List[Dict], str, str]:
    """
    Fetch contracts from SAM.gov API.
    
    Args:
        api_key: SAM.gov API key
        posted_from: Start date in MM/DD/YYYY format (defaults to yesterday)
        posted_to: End date in MM/DD/YYYY format (defaults to yesterday)
        org_code: Organization code (default: 070 for DHS)
        
    Returns:
        Tuple of (contracts list, posted_from date, posted_to date)
    """
    # Default to yesterday if dates not provided
    if not posted_from or not posted_to:
        yesterday = datetime.now() - timedelta(days=1)
        posted_from = yesterday.strftime("%m/%d/%Y")
        posted_to = yesterday.strftime("%m/%d/%Y")
    
    params = {
        "api_key": api_key,
        "organizationCode": org_code,
        "postedFrom": posted_from,
        "postedTo": posted_to,
        "active": "true",
        "limit": 200
    }

    response = requests.get(BASE_URL, params=params, timeout=30)

    if response.status_code == 200:
        data = response.json()
        opportunities = data.get("opportunitiesData", [])
        return opportunities, posted_from, posted_to
    else:
        raise Exception(f"API error: {response.status_code} - {response.text}")


def process_contracts(raw_data: List[Dict]) -> List[Dict]:
    """
    Process and simplify contract data.
    
    Args:
        raw_data: Raw contract data from SAM.gov API
        
    Returns:
        List of processed contract dictionaries
    """
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
