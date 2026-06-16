import os
import requests
from dotenv import load_dotenv

load_dotenv()

FRESHDESK_API_KEY = os.getenv("FRESHDESK_API_KEY")
FRESHDESK_DOMAIN = os.getenv("FRESHDESK_DOMAIN")

if not FRESHDESK_API_KEY or not FRESHDESK_DOMAIN:
    raise ValueError("Freshdesk credentials not found in .env file")

FRESHDESK_URL = f"https://{FRESHDESK_DOMAIN}/api/v2"

def get_freshdesk_tickets(status="open", limit=10):
    """
    Fetch open tickets from Freshdesk
    
    Status options:
    - open: Open tickets
    - pending: Pending tickets
    - resolved: Resolved tickets
    - closed: Closed tickets
    """
    
    try:
        url = f"{FRESHDESK_URL}/tickets"
        params = {
            "status": _status_to_id(status),
            "per_page": limit
        }
        
        response = requests.get(
            url,
            params=params,
            auth=(FRESHDESK_API_KEY, "X"),
            timeout=10
        )
        response.raise_for_status()
        
        tickets = response.json().get("tickets", [])
        
        # Extract relevant fields
        formatted_tickets = []
        for ticket in tickets:
            formatted_tickets.append({
                "id": str(ticket.get("id")),
                "subject": ticket.get("subject", "No subject"),
                "description": ticket.get("description", "No description"),
                "requester_email": ticket.get("requester", {}).get("email", "unknown@company.com"),
                "status": ticket.get("status"),
                "priority": ticket.get("priority"),
                "created_at": ticket.get("created_at"),
                "updated_at": ticket.get("updated_at")
            })
        
        return formatted_tickets
    
    except requests.exceptions.RequestException as e:
        print(f"Error fetching Freshdesk tickets: {e}")
        return []

def _status_to_id(status):
    """Convert status name to Freshdesk status ID"""
    status_map = {
        "open": 2,
        "pending": 3,
        "resolved": 4,
        "closed": 5
    }
    return status_map.get(status.lower(), 2)

def get_ticket_by_id(ticket_id):
    """Fetch a specific ticket by ID"""
    try:
        url = f"{FRESHDESK_URL}/tickets/{ticket_id}"
        
        response = requests.get(
            url,
            auth=(FRESHDESK_API_KEY, "X"),
            timeout=10
        )
        response.raise_for_status()
        
        ticket = response.json()
        
        return {
            "id": str(ticket.get("id")),
            "subject": ticket.get("subject"),
            "description": ticket.get("description"),
            "requester_email": ticket.get("requester", {}).get("email"),
            "status": ticket.get("status"),
            "priority": ticket.get("priority")
        }
    
    except requests.exceptions.RequestException as e:
        print(f"Error fetching ticket {ticket_id}: {e}")
        return None

def update_ticket_status(ticket_id, status):
    """Update ticket status"""
    try:
        url = f"{FRESHDESK_URL}/tickets/{ticket_id}"
        
        payload = {
            "status": _status_to_id(status)
        }
        
        response = requests.put(
            url,
            json=payload,
            auth=(FRESHDESK_API_KEY, "X"),
            timeout=10
        )
        response.raise_for_status()
        
        return True
    
    except requests.exceptions.RequestException as e:
        print(f"Error updating ticket {ticket_id}: {e}")
        return False

def add_ticket_note(ticket_id, note):
    """Add a note to a ticket"""
    try:
        url = f"{FRESHDESK_URL}/tickets/{ticket_id}/notes"
        
        payload = {
            "body": note,
            "notify_emails": []
        }
        
        response = requests.post(
            url,
            json=payload,
            auth=(FRESHDESK_API_KEY, "X"),
            timeout=10
        )
        response.raise_for_status()
        
        return True
    
    except requests.exceptions.RequestException as e:
        print(f"Error adding note to ticket {ticket_id}: {e}")
        return False