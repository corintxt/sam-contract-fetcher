import requests
import csv
from dotenv import load_dotenv
import os
from datetime import datetime, timedelta

# Load environment variables from .env file
load_dotenv()
API_KEY = os.getenv("SAM_API_KEY")

BASE_URL = "https://api.sam.gov/opportunities/v2/search"

def fetch_contracts():
    yesterday = datetime.now() - timedelta(days=1)
    posted_from = yesterday.strftime("%m/%d/%Y")
    posted_to = yesterday.strftime("%m/%d/%Y")

    params = {
        "api_key": API_KEY,
        "organizationCode": "070",  # Example organization code for DHS
        "notice_type": "Solicitation,Sources Sought",
        "postedFrom": posted_from,
        "postedTo": posted_to,
        "active": "true",
        "limit": 200  # Increase limit to get more results
    }

    response = requests.get(BASE_URL, params=params, timeout=30)

    if response.status_code == 200:
        data = response.json()
        return data.get("opportunitiesData", [])
    else:
        print(f"Error fetching contracts: {response.status_code}")
        return []