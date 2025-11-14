#!/usr/bin/env python3
"""
Email notification module.
Handles sending email notifications via Mailgun.
"""

import os
import requests
from typing import List, Dict, Optional


def send_email_notification(
    contracts: List[Dict],
    posted_from: str,
    posted_to: str,
    file_location: str,
    mailgun_api_key: str,
    mailgun_domain: str,
    to_email: str,
    enabled: bool = True
) -> bool:
    """
    Send email notification with contract summary.
    
    Args:
        contracts: List of contract dictionaries
        posted_from: Start date string
        posted_to: End date string
        file_location: Location of saved data (GCS path or local)
        mailgun_api_key: Mailgun API key
        mailgun_domain: Mailgun domain
        to_email: Recipient email address
        enabled: Whether to send email (default: True)
        
    Returns:
        True if email sent successfully, False otherwise
    """
    if not enabled:
        return False
    
    if not all([mailgun_api_key, mailgun_domain, to_email]):
        return False
    
    try:
        # Create email content
        contract_count = len(contracts)
        subject = f"Government Contract Report - {contract_count} contracts found ({posted_from})"
        
        # Generate HTML table of contracts
        contracts_table = _generate_html_table(contracts)
        
        # HTML email body
        html_body = f"""
        <html>
        <body>
            <h2>Government Contract Fetcher Daily Report</h2>
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
        text_body = _generate_text_body(contracts, posted_from, posted_to, file_location)
        
        # Send email via Mailgun
        mailgun_url = f"https://api.mailgun.net/v3/{mailgun_domain}/messages"
        auth = ("api", mailgun_api_key)
        
        data = {
            "from": f"SAM Contract Fetcher <noreply@{mailgun_domain}>",
            "to": to_email,
            "subject": subject,
            "text": text_body,
            "html": html_body
        }
        
        response = requests.post(mailgun_url, auth=auth, data=data, timeout=30)
        
        return response.status_code == 200
            
    except Exception as e:
        return False


def _generate_html_table(contracts: List[Dict]) -> str:
    """Generate HTML table for email body."""
    if not contracts:
        return "<p>No contracts found for this date range.</p>"
    
    table = "<table border='1' cellpadding='5' cellspacing='0' style='border-collapse: collapse; width: 100%;'>"
    table += """
    <tr style='background-color: #f2f2f2;'>
        <th>Title</th>
        <th>Organization</th>
        <th>Solicitation #</th>
        <th>Posted Date</th>
        <th>Deadline</th>
        <th>Type</th>
        <th>Office Location</th>
        <th>Set Aside</th>
    </tr>
    """
    
    for contract in contracts:  # Include all contracts
        table += f"""
        <tr>
            <td><a href="{contract.get('ui_link', '#')}" target="_blank">{contract.get('title', 'N/A')}</a></td>
            <td>{contract.get('organization', 'N/A')}</td>
            <td>{contract.get('solicitation_number', 'N/A')}</td>
            <td>{contract.get('posted_date', 'N/A')}</td>
            <td>{contract.get('response_deadline', 'N/A')}</td>
            <td>{contract.get('type', 'N/A')}</td>
            <td>{contract.get('office_city', 'N/A')}, {contract.get('office_state', 'N/A')}</td>
            <td>{contract.get('set_aside', 'N/A')}</td>
        </tr>
        """
    
    table += "</table>"
    
    return table


def _generate_text_body(
    contracts: List[Dict],
    posted_from: str,
    posted_to: str,
    file_location: str
) -> str:
    """Generate plain text email body."""
    text_body = f"""
DHS Contract Fetcher Daily Report

Date Range: {posted_from} to {posted_to}
Total Contracts Found: {len(contracts)}
Data Location: {file_location}

Contract Details:
"""
    
    for i, contract in enumerate(contracts, 1):  # Include all contracts
        text_body += f"""
{i}. {contract.get('title', 'N/A')}
   Organization: {contract.get('organization', 'N/A')}
   Solicitation: {contract.get('solicitation_number', 'N/A')}
   Posted: {contract.get('posted_date', 'N/A')}
   Deadline: {contract.get('response_deadline', 'N/A')}
   Link: {contract.get('ui_link', 'N/A')}
"""
    
    return text_body
