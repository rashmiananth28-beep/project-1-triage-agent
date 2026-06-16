import json
import time
import os
from datetime import datetime
from typing import Dict, List
import sqlite3

class TokenCounter:
    """
    Tracks API usage, tokens, and costs automatically.
    Works like company monitoring systems.
    """
    
    def __init__(self, employee_id: str, db_path: str = "token_logs.db"):
        """
        Initialize token counter for an employee.
        
        Args:
            employee_id: Unique ID for tracking (e.g., "rashmi-001", "emp-123")
            db_path: Where to store logs
        """
        self.employee_id = employee_id
        self.db_path = db_path
        self.session_start = datetime.now()
        
        # Initialize database
        self._init_db()
    
    def _init_db(self):
        """Create database tables if they don't exist"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Create logs table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS api_calls (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                employee_id TEXT NOT NULL,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                model TEXT NOT NULL,
                input_tokens INTEGER NOT NULL,
                output_tokens INTEGER NOT NULL,
                total_tokens INTEGER NOT NULL,
                cost_usd REAL NOT NULL,
                task_type TEXT,
                notes TEXT
            )
        """)
        
        # Create daily summary table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS daily_summary (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                employee_id TEXT NOT NULL,
                date DATE NOT NULL,
                total_calls INTEGER,
                total_input_tokens INTEGER,
                total_output_tokens INTEGER,
                total_tokens INTEGER,
                total_cost_usd REAL,
                models_used TEXT,
                UNIQUE(employee_id, date)
            )
        """)
        
        conn.commit()
        conn.close()
        
        print(f"✅ Database initialized at {self.db_path}")
    
    def log_api_call(self, 
                    model: str,
                    input_tokens: int,
                    output_tokens: int,
                    task_type: str = "ticket_triage",
                    notes: str = None) -> Dict:
        """
        Log an API call. Call this AFTER every Claude API call.
        
        Args:
            model: Which Claude model ("haiku-4.5", "sonnet-4.6", "opus-4.8", "fable-5")
            input_tokens: Tokens sent to Claude
            output_tokens: Tokens Claude sent back
            task_type: What task (e.g., "ticket_triage", "analysis")
            notes: Any additional info
            
        Returns:
            Dictionary with cost info
        """
        
        # Define pricing (as of June 2026)
        pricing = {
            "haiku-4.5": {"input": 1, "output": 5},
            "sonnet-4.6": {"input": 3, "output": 15},
            "opus-4.8": {"input": 5, "output": 25},
            "fable-5": {"input": 10, "output": 50},
        }
        
        # Get pricing for this model
        if model not in pricing:
            raise ValueError(f"Unknown model: {model}")
        
        price = pricing[model]
        
        # Calculate cost
        input_cost = (input_tokens * price["input"]) / 1_000_000
        output_cost = (output_tokens * price["output"]) / 1_000_000
        total_cost = input_cost + output_cost
        total_tokens = input_tokens + output_tokens
        
        # Log to database
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO api_calls 
            (employee_id, model, input_tokens, output_tokens, total_tokens, cost_usd, task_type, notes)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            self.employee_id,
            model,
            input_tokens,
            output_tokens,
            total_tokens,
            total_cost,
            task_type,
            notes
        ))
        
        conn.commit()
        conn.close()
        
        # Print summary
        print(f"\n📊 API CALL LOGGED:")
        print(f"   Employee: {self.employee_id}")
        print(f"   Model: {model}")
        print(f"   Input tokens: {input_tokens}")
        print(f"   Output tokens: {output_tokens}")
        print(f"   Total tokens: {total_tokens}")
        print(f"   Cost: ${total_cost:.6f} (≈ ₹{total_cost * 82:.2f})")
        print(f"   Task: {task_type}")
        
        return {
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "total_tokens": total_tokens,
            "cost_usd": total_cost,
            "cost_inr": total_cost * 82,
            "model": model
        }
    
    def get_daily_stats(self, date: str = None) -> Dict:
        """
        Get statistics for a specific day.
        
        Args:
            date: Date in format "2026-06-15" (default: today)
            
        Returns:
            Dictionary with daily stats
        """
        if date is None:
            date = datetime.now().strftime("%Y-%m-%d")
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT 
                COUNT(*) as calls,
                SUM(input_tokens) as input_tokens,
                SUM(output_tokens) as output_tokens,
                SUM(total_tokens) as total_tokens,
                SUM(cost_usd) as total_cost
            FROM api_calls
            WHERE employee_id = ? AND DATE(timestamp) = ?
        """, (self.employee_id, date))
        
        result = cursor.fetchone()
        conn.close()
        
        if result[0] == 0:
            return {
                "date": date,
                "employee_id": self.employee_id,
                "calls": 0,
                "input_tokens": 0,
                "output_tokens": 0,
                "total_tokens": 0,
                "cost_usd": 0,
                "cost_inr": 0
            }
        
        calls, input_tokens, output_tokens, total_tokens, total_cost = result
        
        return {
            "date": date,
            "employee_id": self.employee_id,
            "calls": calls,
            "input_tokens": input_tokens or 0,
            "output_tokens": output_tokens or 0,
            "total_tokens": total_tokens or 0,
            "cost_usd": total_cost or 0,
            "cost_inr": (total_cost or 0) * 82
        }
    
    def get_monthly_stats(self, month: str = None) -> Dict:
        """
        Get statistics for a month.
        
        Args:
            month: Format "2026-06" (default: current month)
            
        Returns:
            Dictionary with monthly stats
        """
        if month is None:
            month = datetime.now().strftime("%Y-%m")
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT 
                COUNT(*) as calls,
                SUM(input_tokens) as input_tokens,
                SUM(output_tokens) as output_tokens,
                SUM(total_tokens) as total_tokens,
                SUM(cost_usd) as total_cost,
                GROUP_CONCAT(DISTINCT model) as models
            FROM api_calls
            WHERE employee_id = ? AND strftime('%Y-%m', timestamp) = ?
        """, (self.employee_id, month))
        
        result = cursor.fetchone()
        conn.close()
        
        if result[0] == 0:
            return {
                "month": month,
                "employee_id": self.employee_id,
                "calls": 0,
                "total_tokens": 0,
                "cost_usd": 0,
                "cost_inr": 0
            }
        
        calls, input_tokens, output_tokens, total_tokens, total_cost, models = result
        
        return {
            "month": month,
            "employee_id": self.employee_id,
            "total_calls": calls,
            "input_tokens": input_tokens or 0,
            "output_tokens": output_tokens or 0,
            "total_tokens": total_tokens or 0,
            "cost_usd": total_cost or 0,
            "cost_inr": (total_cost or 0) * 82,
            "models_used": models.split(",") if models else []
        }
    
    def detect_waste(self, threshold_tokens: int = 1000) -> List[Dict]:
        """
        Find API calls that used more tokens than threshold.
        Helps identify wasteful calls.
        
        Args:
            threshold_tokens: Alert if call used more than this
            
        Returns:
            List of high-token calls
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT timestamp, model, input_tokens, output_tokens, total_tokens, cost_usd
            FROM api_calls
            WHERE employee_id = ? AND total_tokens > ?
            ORDER BY total_tokens DESC
            LIMIT 10
        """, (self.employee_id, threshold_tokens))
        
        results = cursor.fetchall()
        conn.close()
        
        waste_list = []
        for timestamp, model, input_tokens, output_tokens, total_tokens, cost in results:
            waste_list.append({
                "timestamp": timestamp,
                "model": model,
                "input_tokens": input_tokens,
                "output_tokens": output_tokens,
                "total_tokens": total_tokens,
                "cost_usd": cost
            })
        
        return waste_list
    
    def generate_report(self) -> str:
        """
        Generate a full monthly report.
        
        Returns:
            Formatted report as string
        """
        month = datetime.now().strftime("%Y-%m")
        monthly = self.get_monthly_stats(month)
        today = datetime.now().strftime("%Y-%m-%d")
        daily = self.get_daily_stats(today)
        waste = self.detect_waste(threshold_tokens=500)
        
        report = f"""
╔════════════════════════════════════════════════════════════════╗
║                    TOKEN USAGE REPORT                          ║
║                    Employee: {self.employee_id:<41} ║
║                    Month: {month:<45} ║
╚════════════════════════════════════════════════════════════════╝

📊 MONTHLY SUMMARY:
   Total API Calls: {monthly['total_calls']}
   Total Tokens: {monthly['total_tokens']:,}
   ├─ Input: {monthly['input_tokens']:,}
   ├─ Output: {monthly['output_tokens']:,}
   Total Cost: ${monthly['cost_usd']:.2f} (₹{monthly['cost_inr']:.2f})
   Models Used: {', '.join(monthly['models_used'])}

📅 TODAY'S ACTIVITY ({today}):
   API Calls: {daily['calls']}
   Tokens: {daily['total_tokens']:,}
   Cost: ${daily['cost_usd']:.6f} (₹{daily['cost_inr']:.2f})

⚠️ WASTE DETECTION (Calls > 500 tokens):
   Found {len(waste)} high-token calls:
"""
        
        for item in waste:
            report += f"\n   • {item['timestamp']}: {item['total_tokens']:,} tokens (${item['cost_usd']:.6f})"
        
        report += f"""

📈 INSIGHTS:
   Average tokens per call: {monthly['total_tokens'] // monthly['total_calls'] if monthly['total_calls'] > 0 else 0:,}
   Average cost per call: ${monthly['cost_usd'] / monthly['total_calls']:.6f}
   Cost per 1000 tokens: ${(monthly['cost_usd'] / monthly['total_tokens'] * 1000) if monthly['total_tokens'] > 0 else 0:.2f}

═══════════════════════════════════════════════════════════════════
Report generated: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
═══════════════════════════════════════════════════════════════════
"""
        
        return report