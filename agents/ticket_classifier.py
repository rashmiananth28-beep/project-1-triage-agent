import os
import json
import requests
import re
import time
from datetime import datetime
from typing import Dict, List, Tuple
from pathlib import Path
from dotenv import load_dotenv
from knowledge_base.loader import search_kb

load_dotenv()

api_key = os.getenv("ANTHROPIC_API_KEY")
if not api_key:
    raise ValueError("ANTHROPIC_API_KEY not found in .env file")

API_URL = "https://api.anthropic.com/v1/messages"
HEADERS = {
    "x-api-key": api_key,
    "anthropic-version": "2023-06-01",
    "content-type": "application/json"
}

# Token tracking configuration
TOKEN_LOG_DIR = "token_logs"
EMPLOYEE_ID = os.getenv("EMPLOYEE_ID", "RASHMI_001")  # Add to .env
TOKEN_LOG_FILE = os.path.join(TOKEN_LOG_DIR, f"{EMPLOYEE_ID}_tokens.json")
DAILY_SUMMARY_FILE = os.path.join(TOKEN_LOG_DIR, "daily_summary.json")

# Ensure log directory exists
Path(TOKEN_LOG_DIR).mkdir(exist_ok=True)

# Model pricing configuration (2026 rates)
MODEL_PRICING = {
    "claude-opus-4-6": {"input": 5, "output": 25},
    "claude-sonnet-4-6": {"input": 3, "output": 15},
    "claude-haiku-4-5": {"input": 1, "output": 5},
    "claude-fable-5": {"input": 10, "output": 50},
}

class TokenCounter:
    """Automatic token counting and cost tracking system"""
    
    def __init__(self, employee_id: str = EMPLOYEE_ID):
        self.employee_id = employee_id
        self.token_log_file = TOKEN_LOG_FILE
        self.daily_summary_file = DAILY_SUMMARY_FILE
        self.today = datetime.now().strftime("%Y-%m-%d")
    
    def estimate_tokens(self, text: str) -> int:
        """Estimate tokens using 1 token ≈ 0.75 words rule"""
        words = len(text.split())
        tokens = int(words / 0.75)
        return max(tokens, 1)  # Minimum 1 token
    
    def log_api_call(self, 
                     ticket_id: str,
                     model: str,
                     input_tokens: int,
                     output_tokens: int,
                     severity: str = None,
                     status: str = None) -> Dict:
        """Log API call with token usage and cost"""
        
        timestamp = datetime.now().isoformat()
        
        # Get pricing for model
        pricing = MODEL_PRICING.get(model, MODEL_PRICING["claude-sonnet-4-6"])
        
        # Calculate costs
        input_cost = (input_tokens * pricing["input"]) / 1_000_000
        output_cost = (output_tokens * pricing["output"]) / 1_000_000
        total_cost = input_cost + output_cost
        
        # Detect token waste (excessive output for simple task)
        is_wasteful = output_tokens > (input_tokens * 10)  # If output > 10x input
        
        # Create log entry
        log_entry = {
            "timestamp": timestamp,
            "ticket_id": ticket_id,
            "employee_id": self.employee_id,
            "model": model,
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "total_tokens": input_tokens + output_tokens,
            "input_cost": round(input_cost, 6),
            "output_cost": round(output_cost, 6),
            "total_cost": round(total_cost, 6),
            "severity": severity,
            "status": status,
            "is_wasteful": is_wasteful,
            "waste_ratio": round(output_tokens / input_tokens if input_tokens > 0 else 0, 2)
        }
        
        # Append to log file
        self._append_to_log(log_entry)
        
        return log_entry
    
    def _append_to_log(self, log_entry: Dict):
        """Append log entry to employee's token log"""
        logs = []
        
        if os.path.exists(self.token_log_file):
            try:
                with open(self.token_log_file, 'r') as f:
                    logs = json.load(f)
            except:
                logs = []
        
        logs.append(log_entry)
        
        with open(self.token_log_file, 'w') as f:
            json.dump(logs, f, indent=2)
    
    def get_daily_summary(self) -> Dict:
        """Get daily token usage summary"""
        if not os.path.exists(self.token_log_file):
            return self._empty_summary()
        
        with open(self.token_log_file, 'r') as f:
            logs = json.load(f)
        
        # Filter logs for today
        today_logs = [log for log in logs if log["timestamp"].startswith(self.today)]
        
        if not today_logs:
            return self._empty_summary()
        
        summary = {
            "date": self.today,
            "employee_id": self.employee_id,
            "total_calls": len(today_logs),
            "total_input_tokens": sum(log["input_tokens"] for log in today_logs),
            "total_output_tokens": sum(log["output_tokens"] for log in today_logs),
            "total_tokens": sum(log["total_tokens"] for log in today_logs),
            "total_cost": round(sum(log["total_cost"] for log in today_logs), 6),
            "model_breakdown": self._get_model_breakdown(today_logs),
            "wasteful_calls": len([log for log in today_logs if log["is_wasteful"]]),
            "average_waste_ratio": round(
                sum(log["waste_ratio"] for log in today_logs) / len(today_logs) if today_logs else 0, 2
            ),
            "timestamp": datetime.now().isoformat()
        }
        
        return summary
    
    def _get_model_breakdown(self, logs: List[Dict]) -> Dict:
        """Get token usage breakdown by model"""
        breakdown = {}
        
        for log in logs:
            model = log["model"]
            if model not in breakdown:
                breakdown[model] = {
                    "calls": 0,
                    "input_tokens": 0,
                    "output_tokens": 0,
                    "total_tokens": 0,
                    "cost": 0
                }
            
            breakdown[model]["calls"] += 1
            breakdown[model]["input_tokens"] += log["input_tokens"]
            breakdown[model]["output_tokens"] += log["output_tokens"]
            breakdown[model]["total_tokens"] += log["total_tokens"]
            breakdown[model]["cost"] += log["total_cost"]
        
        # Round costs
        for model in breakdown:
            breakdown[model]["cost"] = round(breakdown[model]["cost"], 6)
        
        return breakdown
    
    def _empty_summary(self) -> Dict:
        """Return empty summary"""
        return {
            "date": self.today,
            "employee_id": self.employee_id,
            "total_calls": 0,
            "total_input_tokens": 0,
            "total_output_tokens": 0,
            "total_tokens": 0,
            "total_cost": 0,
            "model_breakdown": {},
            "wasteful_calls": 0,
            "average_waste_ratio": 0,
            "timestamp": datetime.now().isoformat()
        }
    
    def print_summary(self):
        """Print formatted daily summary to console"""
        summary = self.get_daily_summary()
        
        print("\n" + "="*70)
        print(f"TOKEN USAGE SUMMARY - {summary['date']}")
        print(f"Employee: {summary['employee_id']}")
        print("="*70)
        print(f"Total API Calls: {summary['total_calls']}")
        print(f"Total Tokens Used: {summary['total_tokens']:,}")
        print(f"  ├─ Input: {summary['total_input_tokens']:,}")
        print(f"  └─ Output: {summary['total_output_tokens']:,}")
        print(f"Total Cost: ${summary['total_cost']:.6f}")
        print(f"Wasteful Calls: {summary['wasteful_calls']} (avg waste ratio: {summary['average_waste_ratio']})")
        
        if summary['model_breakdown']:
            print("\nModel Breakdown:")
            for model, data in summary['model_breakdown'].items():
                print(f"  {model}:")
                print(f"    Calls: {data['calls']}")
                print(f"    Tokens: {data['total_tokens']:,}")
                print(f"    Cost: ${data['cost']:.6f}")
        
        print("="*70 + "\n")

# Initialize token counter
token_counter = TokenCounter(EMPLOYEE_ID)

def extract_json(text: str) -> str:
    """Extract JSON from text, handling markdown code blocks"""
    try:
        # Try to find JSON in markdown code blocks
        json_match = re.search(r'```(?:json)?\s*(.*?)\s*```', text, re.DOTALL)
        if json_match:
            return json_match.group(1).strip()
        
        # Try to find raw JSON
        json_match = re.search(r'\{.*\}', text, re.DOTALL)
        if json_match:
            return json_match.group(0).strip()
        
        return text.strip()
    except Exception as e:
        print(f"Error extracting JSON: {e}")
        return text.strip()

def call_claude_api(prompt: str, model: str = "claude-sonnet-4-6") -> Tuple[str, int, int]:
    """Call Claude API and return response with token counts"""
    
    # Estimate input tokens
    input_tokens_estimated = token_counter.estimate_tokens(prompt)
    
    payload = {
        "model": model,
        "max_tokens": 1000,
        "messages": [{"role": "user", "content": prompt}]
    }
    
    try:
        print(f"   Calling Claude API (Model: {model})...")
        response = requests.post(API_URL, headers=HEADERS, json=payload, timeout=30)
        response.raise_for_status()
        
        result = response.json()
        response_text = result['content'][0]['text'].strip()
        
        # Estimate output tokens
        output_tokens_estimated = token_counter.estimate_tokens(response_text)
        
        print(f"   ✅ Response received")
        print(f"   Tokens - Input: {input_tokens_estimated}, Output: {output_tokens_estimated}")
        
        return response_text, input_tokens_estimated, output_tokens_estimated
    
    except requests.exceptions.RequestException as e:
        print(f"Error calling Claude API: {e}")
        return f"Error: {str(e)}", input_tokens_estimated, 0

def classify_and_resolve_ticket(ticket_data: Dict, employee_id: str = EMPLOYEE_ID):
    """Classify ticket and find resolution with automatic token tracking"""
    
    print(f"\n📝 Processing Ticket: {ticket_data['ticket_id']}")
    print(f"👤 Employee: {employee_id}")
    
    ticket_text = f"""
Ticket ID: {ticket_data['ticket_id']}
Title: {ticket_data['title']}
Description: {ticket_data['description']}
Requester: {ticket_data.get('requester_email', 'unknown')}
"""
    
    system_prompt = """You are an intelligent IT support triage agent. Your job is to:

1. CLASSIFY the ticket severity (critical/high/medium/low)
2. SEARCH the knowledge base for similar issues
3. SUGGEST a resolution if one exists, OR
4. ESCALATE to human support with your findings

Be thorough but decisive. Use the tools provided to help you."""
    
    severity = "medium"
    resolution = "Unable to resolve automatically"
    escalation_needed = True
    status = "escalated"
    
    # STEP 1: Classify Severity
    print("\n[Step 1] Classifying severity...")
    classify_prompt = f"""You are an IT support triage agent. Classify this ticket severity.

{ticket_text}

Respond ONLY with valid JSON (no markdown):
{{"severity": "critical|high|medium|low", "reasoning": "brief reasoning"}}"""

    response_text, input_tokens, output_tokens = call_claude_api(classify_prompt)
    
    # Log this API call
    token_counter.log_api_call(
        ticket_id=ticket_data['ticket_id'],
        model="claude-sonnet-4-6",
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        severity="classification"
    )
    
    try:
        json_text = extract_json(response_text)
        severity_data = json.loads(json_text)
        severity = severity_data.get("severity", "medium")
        print(f"   Severity: {severity}")
    except Exception as e:
        print(f"   ⚠️ Error parsing severity: {e}")
        severity = "medium"
    
    # STEP 2: Search Knowledge Base
    print("\n[Step 2] Searching knowledge base...")
    search_query = f"{ticket_data['title']} {ticket_data['description']}"
    kb_results = search_kb(search_query)
    print(f"   Found {len(kb_results)} matching solutions")
    
    # STEP 3: Get Resolution
    print("\n[Step 3] Finding resolution...")
    
    kb_text = "No knowledge base matches found"
    if kb_results:
        kb_text = "Knowledge base results:\n"
        for result in kb_results:
            kb_text += f"\n- {result['issue']}: {result['solution'][:100]}..."
    
    resolution_prompt = f"""You are an IT support triage agent. Based on this ticket and knowledge base, decide if it can be auto-resolved.

Ticket:
{ticket_text}

{kb_text}

Respond ONLY with valid JSON (no markdown):
{{"can_resolve": true/false, "resolution": "solution or escalation reason"}}"""

    response_text, input_tokens, output_tokens = call_claude_api(resolution_prompt)
    
    # Log this API call
    token_counter.log_api_call(
        ticket_id=ticket_data['ticket_id'],
        model="claude-sonnet-4-6",
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        severity=severity
    )
    
    try:
        json_text = extract_json(response_text)
        resolution_data = json.loads(json_text)
        can_resolve = resolution_data.get("can_resolve", False)
        resolution = resolution_data.get("resolution", "Unable to resolve")
        
        if can_resolve:
            status = "resolved"
            escalation_needed = False
            print(f"   Status: RESOLVED ✅")
        else:
            status = "escalated"
            escalation_needed = True
            print(f"   Status: ESCALATED ⚠️")
    except Exception as e:
        print(f"   ⚠️ Error parsing resolution: {e}")
        resolution = "Unable to resolve automatically"
        escalation_needed = True
        status = "escalated"
    
    # Print daily summary at the end
    token_counter.print_summary()
    
    return {
        "ticket_id": ticket_data['ticket_id'],
        "severity": severity,
        "status": status,
        "suggested_resolution": resolution,
        "escalation_needed": escalation_needed,
        "employee_id": employee_id
    }