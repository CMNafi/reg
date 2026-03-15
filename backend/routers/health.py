import os
from datetime import datetime, timezone
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from db.models import get_db, Firm, RiskFlag

router = APIRouter()


@router.get("/health")
def health(db: Session = Depends(get_db)):
    db_ok = True
    total_firms = 0
    verified_firms = 0
    ai_estimated = 0
    active_flags = 0
    critical_flags = 0

    try:
        total_firms = db.query(Firm).count()
        verified_firms = db.query(Firm).filter(Firm.data_source == "SEC_IAPD").count()
        ai_estimated = db.query(Firm).filter(Firm.data_source == "AI_EXTRACTED").count()
        active_flags = db.query(RiskFlag).filter(RiskFlag.is_active == True).count()
        critical_flags = db.query(RiskFlag).filter(
            RiskFlag.is_active == True,
            RiskFlag.severity == "CRITICAL",
        ).count()
    except Exception:
        db_ok = False

    api_key = os.getenv("ANTHROPIC_API_KEY", "")
    claude_ok = api_key.startswith("sk-ant") if api_key else False

    return {
        "status": "online" if db_ok else "degraded",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "db": "connected" if db_ok else "error",
        "total_firms": total_firms,
        "verified_firms": verified_firms,
        "ai_estimated": ai_estimated,
        "active_flags": active_flags,
        "critical_flags": critical_flags,
        "claude_api": "configured" if claude_ok else "not_configured",
    }
