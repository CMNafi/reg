import asyncio
from fastapi import APIRouter, Depends, BackgroundTasks, HTTPException
from sqlalchemy.orm import Session
from datetime import datetime, timezone

from db.models import (
    get_db, Firm, Disclosure, ChangeEvent, RiskFlag,
    KeyPerson, HoldingSnapshot, Holding
)
from data.fetch_adv import get_adv_by_crd, normalize_iapd, parse_disclosures
from data.fetch_13f import get_13f_holdings
from data.detect_changes import detect_changes
from data.red_flags import generate_flags

router = APIRouter()


@router.get("/firms/{crd}")
def get_firm(crd: str, db: Session = Depends(get_db)):
    firm = db.query(Firm).filter(Firm.crd_number == crd).first()
    if not firm:
        raise HTTPException(status_code=404, detail="Firm not found")

    disclosures = (
        db.query(Disclosure)
        .filter(Disclosure.firm_crd == crd)
        .all()
    )

    changes = (
        db.query(ChangeEvent)
        .filter(ChangeEvent.firm_crd == crd)
        .order_by(ChangeEvent.created_at.desc())
        .limit(20)
        .all()
    )

    flags = (
        db.query(RiskFlag)
        .filter(RiskFlag.firm_crd == crd, RiskFlag.is_active == True)
        .all()
    )

    persons = (
        db.query(KeyPerson)
        .filter(KeyPerson.firm_crd == crd)
        .all()
    )

    snapshot = (
        db.query(HoldingSnapshot)
        .filter(HoldingSnapshot.firm_crd == crd)
        .order_by(HoldingSnapshot.created_at.desc())
        .first()
    )

    return {
        "firm": firm.to_dict(),
        "disclosures": [d.to_dict() for d in disclosures],
        "changes": [c.to_dict() for c in changes],
        "flags": [f.to_dict() for f in flags],
        "key_persons": [p.to_dict() for p in persons],
        "holding_snapshot": snapshot.to_dict() if snapshot else None,
    }


@router.get("/firms/{crd}/holdings")
def get_firm_holdings(crd: str, db: Session = Depends(get_db)):
    snapshot = (
        db.query(HoldingSnapshot)
        .filter(HoldingSnapshot.firm_crd == crd)
        .order_by(HoldingSnapshot.created_at.desc())
        .first()
    )

    holdings = (
        db.query(Holding)
        .filter(Holding.firm_crd == crd)
        .order_by(Holding.market_value.desc())
        .limit(25)
        .all()
    )

    return {
        "snapshot": snapshot.to_dict() if snapshot else None,
        "holdings": [h.to_dict() for h in holdings],
    }


@router.get("/firms/{crd}/peers")
def get_firm_peers(crd: str, db: Session = Depends(get_db)):
    firm = db.query(Firm).filter(Firm.crd_number == crd).first()
    if not firm:
        raise HTTPException(status_code=404, detail="Firm not found")

    query = db.query(Firm).filter(Firm.crd_number != crd)

    candidates = []
    if firm.aum_total and firm.aum_total > 0:
        low = firm.aum_total * 0.5
        high = firm.aum_total * 1.5
        aum_matches = query.filter(
            Firm.aum_total >= low,
            Firm.aum_total <= high,
        ).all()

        for peer in aum_matches:
            if peer.state == firm.state or peer.primary_strategy == firm.primary_strategy:
                candidates.append(peer)

    if not candidates and firm.aum_total:
        low = firm.aum_total * 0.5
        high = firm.aum_total * 1.5
        candidates = query.filter(
            Firm.aum_total >= low,
            Firm.aum_total <= high,
        ).limit(4).all()

    candidates.sort(key=lambda p: p.aum_total or 0, reverse=True)
    peers = candidates[:4]

    result = []
    for peer in peers:
        flags = (
            db.query(RiskFlag)
            .filter(RiskFlag.firm_crd == peer.crd_number, RiskFlag.is_active == True)
            .all()
        )
        result.append({
            "firm": peer.to_dict(),
            "flags": [f.to_dict() for f in flags],
        })

    return {"peers": result}


def _run_refresh(crd: str):
    from db.models import SessionLocal
    db = SessionLocal()
    try:
        firm = db.query(Firm).filter(Firm.crd_number == crd).first()
        if not firm:
            return

        prev_dict = firm.to_dict()

        raw_adv = asyncio.run(get_adv_by_crd(crd))
        if raw_adv:
            firm_data = normalize_iapd(raw_adv)
            if firm.employee_count:
                firm_data["employee_count_prior"] = firm.employee_count
            for key, val in firm_data.items():
                if hasattr(firm, key) and key != "crd_number":
                    setattr(firm, key, val)
            firm.updated_at = datetime.now(timezone.utc)

            db.query(Disclosure).filter(Disclosure.firm_crd == crd).delete()
            raw_disc = raw_adv.get("data", {}).get("disclosures", [])
            for d in parse_disclosures(raw_disc):
                d["firm_crd"] = crd
                db.add(Disclosure(**d))

        if firm.cik:
            holdings_data = get_13f_holdings(firm.cik)
            if holdings_data:
                firm.last_13f_date = holdings_data.get("period_end")
                db.query(Holding).filter(Holding.firm_crd == crd).delete()
                for h in holdings_data.get("holdings", []):
                    h["firm_crd"] = crd
                    h["period_end"] = holdings_data.get("period_end")
                    db.add(Holding(**{k: v for k, v in h.items() if hasattr(Holding, k)}))
                db.add(HoldingSnapshot(
                    firm_crd=crd,
                    period_end=holdings_data.get("period_end"),
                    total_value=holdings_data.get("total_value"),
                    holding_count=holdings_data.get("holding_count"),
                    top10_concentration=holdings_data.get("top10_concentration"),
                    largest_position_pct=holdings_data.get("largest_position_pct"),
                ))

        db.commit()

        curr_dict = db.query(Firm).filter(Firm.crd_number == crd).first().to_dict()
        changes = detect_changes(prev_dict, curr_dict)
        for c in changes:
            c["firm_crd"] = crd
            db.add(ChangeEvent(**c))

        db.query(RiskFlag).filter(RiskFlag.firm_crd == crd).delete()
        holdings_data_for_flags = {}
        snap = db.query(HoldingSnapshot).filter(HoldingSnapshot.firm_crd == crd).order_by(HoldingSnapshot.created_at.desc()).first()
        if snap:
            holdings_data_for_flags = snap.to_dict()
        flags = generate_flags(curr_dict, changes, holdings_data_for_flags)
        for f in flags:
            f["firm_crd"] = crd
            db.add(RiskFlag(**{k: v for k, v in f.items() if hasattr(RiskFlag, k)}))

        db.commit()
    finally:
        db.close()


@router.post("/firms/{crd}/refresh")
def refresh_firm(crd: str, background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    firm = db.query(Firm).filter(Firm.crd_number == crd).first()
    if not firm:
        raise HTTPException(status_code=404, detail="Firm not found")

    background_tasks.add_task(_run_refresh, crd)
    return {"status": "refresh_started", "crd": crd}
