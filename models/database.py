import sqlite3
import json
import os
from datetime import datetime

DB_PATH = "tickets.db"

def init_db():
    """Initialize SQLite database with tables"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Create tickets table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS tickets (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ticket_id TEXT UNIQUE NOT NULL,
            title TEXT NOT NULL,
            description TEXT,
            requester_email TEXT,
            severity TEXT,
            status TEXT,
            suggested_resolution TEXT,
            escalation_needed BOOLEAN,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    # Create audit log table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS audit_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ticket_id TEXT NOT NULL,
            action TEXT,
            details TEXT,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (ticket_id) REFERENCES tickets(ticket_id)
        )
    """)
    
    # Create metrics table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS metrics (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date DATE,
            total_tickets INTEGER,
            resolved_tickets INTEGER,
            escalated_tickets INTEGER,
            avg_severity TEXT,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    conn.commit()
    conn.close()
    print("✅ Database initialized successfully")

def save_ticket_result(result):
    """Save ticket triage result to database"""
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT OR REPLACE INTO tickets 
            (ticket_id, severity, status, suggested_resolution, escalation_needed, updated_at)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (
            result['ticket_id'],
            result['severity'],
            result['status'],
            result['suggested_resolution'],
            result['escalation_needed'],
            datetime.now()
        ))
        
        # Log the action
        cursor.execute("""
            INSERT INTO audit_log (ticket_id, action, details)
            VALUES (?, ?, ?)
        """, (
            result['ticket_id'],
            'TRIAGE_COMPLETED',
            json.dumps(result)
        ))
        
        conn.commit()
        conn.close()
        
        print(f"✅ Ticket {result['ticket_id']} saved to database")
        return True
    
    except Exception as e:
        print(f"❌ Error saving ticket: {e}")
        return False

def get_ticket_by_id(ticket_id):
    """Retrieve a ticket from database"""
    try:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT * FROM tickets WHERE ticket_id = ?
        """, (ticket_id,))
        
        row = cursor.fetchone()
        conn.close()
        
        if row:
            return dict(row)
        return None
    
    except Exception as e:
        print(f"Error retrieving ticket: {e}")
        return None

def get_all_tickets(limit=50, status=None):
    """Get all tickets from database"""
    try:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        if status:
            cursor.execute("""
                SELECT * FROM tickets WHERE status = ? ORDER BY created_at DESC LIMIT ?
            """, (status, limit))
        else:
            cursor.execute("""
                SELECT * FROM tickets ORDER BY created_at DESC LIMIT ?
            """, (limit,))
        
        rows = cursor.fetchall()
        conn.close()
        
        return [dict(row) for row in rows]
    
    except Exception as e:
        print(f"Error retrieving tickets: {e}")
        return []

def get_metrics(days=7):
    """Get ticket metrics for last N days"""
    try:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT 
                COUNT(*) as total,
                SUM(CASE WHEN status = 'resolved' THEN 1 ELSE 0 END) as resolved,
                SUM(CASE WHEN escalation_needed = 1 THEN 1 ELSE 0 END) as escalated
            FROM tickets
            WHERE created_at >= datetime('now', '-' || ? || ' days')
        """, (days,))
        
        row = cursor.fetchone()
        conn.close()
        
        if row:
            return {
                "total_tickets": row['total'] or 0,
                "resolved_tickets": row['resolved'] or 0,
                "escalated_tickets": row['escalated'] or 0,
                "resolution_rate": round((row['resolved'] or 0) / (row['total'] or 1) * 100, 2)
            }
        
        return {
            "total_tickets": 0,
            "resolved_tickets": 0,
            "escalated_tickets": 0,
            "resolution_rate": 0
        }
    
    except Exception as e:
        print(f"Error retrieving metrics: {e}")
        return None

def get_severity_distribution():
    """Get distribution of ticket severities"""
    try:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT severity, COUNT(*) as count
            FROM tickets
            GROUP BY severity
        """)
        
        rows = cursor.fetchall()
        conn.close()
        
        return {row['severity']: row['count'] for row in rows}
    
    except Exception as e:
        print(f"Error retrieving severity distribution: {e}")
        return {}

def delete_old_tickets(days=90):
    """Delete tickets older than N days"""
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        cursor.execute("""
            DELETE FROM tickets
            WHERE created_at < datetime('now', '-' || ? || ' days')
        """, (days,))
        
        deleted = cursor.rowcount
        conn.commit()
        conn.close()
        
        print(f"✅ Deleted {deleted} old tickets")
        return deleted
    
    except Exception as e:
        print(f"Error deleting old tickets: {e}")
        return 0

def export_tickets_to_json(filename="tickets_export.json"):
    """Export all tickets to JSON file"""
    try:
        tickets = get_all_tickets(limit=10000)
        
        with open(filename, 'w') as f:
            json.dump(tickets, f, indent=2, default=str)
        
        print(f"✅ Exported {len(tickets)} tickets to {filename}")
        return True
    
    except Exception as e:
        print(f"Error exporting tickets: {e}")
        return False