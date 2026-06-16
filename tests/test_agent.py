import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agents.ticket_classifier import classify_and_resolve_ticket

def test_password_reset_ticket():
    """Test with a simple password reset ticket"""
    ticket = {
        "ticket_id": "TKT-001",
        "title": "Cannot reset password",
        "description": "I forgot my password and can't login to the system",
        "requester_email": "user@company.com"
    }
    
    print("\n" + "="*60)
    print("TEST 1: Password Reset Ticket")
    print("="*60)
    
    result = classify_and_resolve_ticket(ticket)
    
    print("\n📋 RESULT:")
    print(f"  Ticket ID: {result['ticket_id']}")
    print(f"  Severity: {result['severity']}")
    print(f"  Status: {result['status']}")
    print(f"  Resolution: {result['suggested_resolution'][:100]}...")
    print(f"  Escalation: {result['escalation_needed']}")
    
    assert result['ticket_id'] == "TKT-001"
    assert result['severity'] in ["critical", "high", "medium", "low"]
    print("\n✅ Test passed!")

def test_vpn_ticket():
    """Test with a VPN issue"""
    ticket = {
        "ticket_id": "TKT-002",
        "title": "VPN not connecting",
        "description": "I can't connect to the corporate VPN. I keep getting an authentication error",
        "requester_email": "user@company.com"
    }
    
    print("\n" + "="*60)
    print("TEST 2: VPN Connection Ticket")
    print("="*60)
    
    result = classify_and_resolve_ticket(ticket)
    
    print("\n📋 RESULT:")
    print(f"  Ticket ID: {result['ticket_id']}")
    print(f"  Severity: {result['severity']}")
    print(f"  Status: {result['status']}")
    print(f"  Escalation: {result['escalation_needed']}")
    
    assert result['ticket_id'] == "TKT-002"
    print("\n✅ Test passed!")

def test_slow_laptop_ticket():
    """Test with a performance issue"""
    ticket = {
        "ticket_id": "TKT-003",
        "title": "My laptop is running very slow",
        "description": "Everything is taking forever. Programs are freezing. What should I do?",
        "requester_email": "user@company.com"
    }
    
    print("\n" + "="*60)
    print("TEST 3: Slow Laptop Ticket")
    print("="*60)
    
    result = classify_and_resolve_ticket(ticket)
    
    print("\n📋 RESULT:")
    print(f"  Ticket ID: {result['ticket_id']}")
    print(f"  Severity: {result['severity']}")
    print(f"  Status: {result['status']}")
    print(f"  Resolution: {result['suggested_resolution'][:100]}...")
    
    assert result['ticket_id'] == "TKT-003"
    print("\n✅ Test passed!")

if __name__ == "__main__":
    test_password_reset_ticket()
    test_vpn_ticket()
    test_slow_laptop_ticket()
    print("\n" + "="*60)
    print("🎉 All tests passed!")
    print("="*60)