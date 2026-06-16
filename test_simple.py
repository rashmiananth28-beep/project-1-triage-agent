from utils.token_counter import TokenCounter
from agents.ticket_classifier import classify_and_resolve_ticket

# Initialize tracker for yourself
tracker = TokenCounter(employee_id="rashmi-001")

# Test with a ticket
ticket = {
    "ticket_id": "TKT-001",
    "title": "Cannot reset password",
    "description": "I forgot my password...",
    "requester_email": "user@company.com"
}

# Process ticket (this automatically logs tokens)
result = classify_and_resolve_ticket(ticket, employee_id="rashmi-001")

# View daily report
print(tracker.generate_report())

# Check for waste
waste = tracker.detect_waste(threshold_tokens=500)
if waste:
    print(f"⚠️ Found {len(waste)} high-token calls")