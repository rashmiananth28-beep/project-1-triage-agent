from fastapi import FastAPI, HTTPException, Security
from fastapi.security.api_key import APIKeyHeader
from fastapi.responses import JSONResponse
from pydantic import BaseModel
import os
from dotenv import load_dotenv
from agents.ticket_classifier import classify_and_resolve_ticket
from utils.token_counter import TokenCounter

load_dotenv()

# Initialize FastAPI app
app = FastAPI(
    title="IT Triage Agent",
    description="Intelligent IT support ticket triage using Claude AI",
    version="2.0"
)

# Initialize Token Counter (SQLite-based)
token_counter = TokenCounter(employee_id="rashmi-user-001")

# API Key Authentication
API_KEY = os.getenv("TRIAGE_API_KEY", "rashmi-triage-secret-key")
api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)

async def verify_api_key(api_key: str = Security(api_key_header)):
    """Verify API key for protected endpoints"""
    if api_key != API_KEY:
        raise HTTPException(
            status_code=401,
            detail="Invalid or missing API key. Pass X-API-Key header."
        )
    return api_key

# ==================== MODELS ====================

class TicketInput(BaseModel):
    ticket_id: str
    title: str
    description: str
    requester_email: str = "user@company.com"

class ResolutionOutput(BaseModel):
    ticket_id: str
    severity: str
    status: str
    suggested_resolution: str
    escalation_needed: bool
    employee_id: str

# ==================== MAIN ENDPOINTS ====================

@app.post("/triage", response_model=ResolutionOutput)
async def triage_ticket(ticket: TicketInput, api_key: str = Security(verify_api_key)):
    """
    Main endpoint: Takes a ticket and uses Claude to:
    1. Classify severity
    2. Search knowledge base
    3. Suggest resolution or escalate
    """
    try:
        # Run ticket through classifier
        result = classify_and_resolve_ticket(ticket.model_dump())

        # Estimate tokens for this triage call
        estimated_input = 200 + len(ticket.title.split()) + len(ticket.description.split())
        estimated_output = len(result.get("suggested_resolution", "").split()) + 20

        # Log to SQLite token counter
        token_counter.log_api_call(
            model="claude-sonnet-4-6",
            input_tokens=int(estimated_input),
            output_tokens=int(estimated_output),
            task_type="ticket_triage",
            notes=f"Ticket: {ticket.ticket_id} | Severity: {result.get('severity', 'unknown')} | Status: {result.get('status', 'unknown')}"
        )

        # Return only ResolutionOutput fields (strip extra keys from result)
        return ResolutionOutput(
            ticket_id=result["ticket_id"],
            severity=result["severity"],
            status=result["status"],
            suggested_resolution=result["suggested_resolution"],
            escalation_needed=result["escalation_needed"],
            employee_id=result["employee_id"]
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ==================== HEALTH CHECK ====================

@app.get("/health")
async def health():
    """Public health check endpoint"""
    return {
        "status": "ok",
        "version": "2.0",
        "api_key_loaded": bool(os.getenv("ANTHROPIC_API_KEY")),
        "freshdesk_configured": bool(os.getenv("FRESHDESK_API_KEY")),
        "token_counter": "✅ Active"
    }

# ==================== TOKEN REPORT ENDPOINTS ====================

@app.get("/token-report/daily")
async def get_daily_token_report(api_key: str = Security(verify_api_key)):
    """Get today's token usage report"""
    try:
        report = token_counter.get_daily_stats()
        return {"success": True, "report": report}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/token-report/monthly")
async def get_monthly_token_report(api_key: str = Security(verify_api_key)):
    """Get this month's token usage report"""
    try:
        report = token_counter.get_monthly_stats()
        return {"success": True, "report": report}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/token-report/full")
async def get_full_token_report(api_key: str = Security(verify_api_key)):
    """Get full formatted report with waste detection"""
    try:
        report = token_counter.generate_report()
        return {"success": True, "report": report}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ==================== ERROR HANDLERS ====================

@app.exception_handler(HTTPException)
async def http_exception_handler(request, exc):
    return JSONResponse(
        status_code=exc.status_code,
        content={"error": exc.detail}
    )

# ==================== RUN SERVER ====================

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)