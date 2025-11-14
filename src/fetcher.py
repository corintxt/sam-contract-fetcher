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
    org_codes: Optional[List[str]] = None
) -> Tuple[List[Dict], str, str]:
    """
    Fetch contracts from SAM.gov API.
    
    Args:
        api_key: SAM.gov API key
        posted_from: Start date in MM/DD/YYYY format (defaults to yesterday)
        posted_to: End date in MM/DD/YYYY format (defaults to yesterday)
        org_codes: List of organization codes (default: ["070"] for DHS)
        
    Returns:
        Tuple of (contracts list, posted_from date, posted_to date)
    """
    # Default org codes if not provided
    if org_codes is None:
        org_codes = ["070"]
    
    # Default to yesterday if dates not provided
    if not posted_from or not posted_to:
        yesterday = datetime.now() - timedelta(days=1)
        posted_from = yesterday.strftime("%m/%d/%Y")
        posted_to = yesterday.strftime("%m/%d/%Y")
    
    # Fetch contracts for each org code separately and combine results
    all_opportunities = []
    seen_notice_ids = set()  # To avoid duplicates
    
    for org_code in org_codes:
        print(f"Fetching contracts for org code: {org_code}")
        
        params = {
            "api_key": api_key,
            "organizationCode": org_code,
            "postedFrom": posted_from,
            "postedTo": posted_to,
            "active": "true",
            "limit": 200
        }

        response = requests.get(BASE_URL, params=params, timeout=30)
        
        # Debug: Print the actual URL being called
        # print(f"DEBUG: API URL: {response.url}")
        print(f"Status Code: {response.status_code}")

        if response.status_code == 200:
            data = response.json()
            opportunities = data.get("opportunitiesData", [])
            print(f"DEBUG: Found {len(opportunities)} contracts for org {org_code}")
            
            # Add unique contracts only
            for opp in opportunities:
                notice_id = opp.get("noticeId")
                if notice_id and notice_id not in seen_notice_ids:
                    seen_notice_ids.add(notice_id)
                    all_opportunities.append(opp)
        else:
            print(f"WARNING: API error for org {org_code}: {response.status_code} - {response.text[:200]}")
            # Continue with other org codes instead of failing completely
    
    print(f"DEBUG: Total unique contracts across all orgs: {len(all_opportunities)}")
    return all_opportunities, posted_from, posted_to


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
