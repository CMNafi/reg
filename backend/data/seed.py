import asyncio
from datetime import datetime, timezone

from db.models import (
    SessionLocal, Firm, Holding, HoldingSnapshot,
    Disclosure, ChangeEvent, RiskFlag
)
from data.fetch_adv import get_adv_by_crd, normalize_iapd, parse_disclosures
from data.fetch_13f import get_13f_holdings
from data.detect_changes import detect_changes
from data.red_flags import generate_flags

SEED_FIRMS = [
    {"name": "Bridgewater Associates",    "crd": "105063", "cik": "1350694"},
    {"name": "Renaissance Technologies", "crd": "106661", "cik": "1037389"},
    {"name": "Two Sigma Investments",     "crd": "137137", "cik": "1179392"},
    {"name": "Citadel Advisors",          "crd": "148826", "cik": "1423053"},
    {"name": "Millennium Management",     "crd": "158117", "cik": "1273087"},
]

VALIDATION_FIELDS = [
    "legal_name", "crd_number", "aum_total", "aum_discretionary",
    "employee_count", "client_count", "city", "state",
    "registration_date", "ownership_structure", "has_criminal_drp",
    "has_regulatory_drp", "drp_count", "data_source", "cik",
]


def _count_populated(firm_dict: dict) -> int:
    count = 0
    for f in VALIDATION_FIELDS:
        val = firm_dict.get(f)
        if val is not None and val != "" and val != 0 and val is not False:
            # has_criminal_drp and has_regulatory_drp: False is a valid populated value
            if f in ("has_criminal_drp", "has_regulatory_drp"):
                count += 1
            elif val:
                count += 1
    return count


async def seed_all_firms(db=None):
    close_db = False
    if db is None:
        db = SessionLocal()
        close_db = True

    try:
        failures = []

        for seed in SEED_FIRMS:
            name = seed["name"]
            crd = seed["crd"]
            cik = seed["cik"]
            print(f"  Seeding {name} (CRD: {crd}, CIK: {cik})...")

            # Fetch ADV data
            raw_adv = await get_adv_by_crd(crd)
            if raw_adv:
                firm_data = normalize_iapd(raw_adv)
            else:
                firm_data = {
                    "crd_number": crd,
                    "legal_name": name,
                    "data_source": "FALLBACK",
                    "data_verified_at": datetime.now(timezone.utc).isoformat(),
                }

            firm_data["cik"] = cik
            if not firm_data.get("legal_name"):
                firm_data["legal_name"] = name

            # Fetch 13F holdings
            holdings_data = get_13f_holdings(cik)

            if holdings_data:
                firm_data["last_13f_date"] = holdings_data.get("period_end")

            # Upsert firm
            existing = db.query(Firm).filter(Firm.crd_number == crd).first()
            prev_dict = existing.to_dict() if existing else None

            if existing:
                # Preserve employee_count_prior
                if firm_data.get("employee_count") and existing.employee_count:
                    firm_data["employee_count_prior"] = existing.employee_count
                for key, val in firm_data.items():
                    if hasattr(existing, key) and key != "crd_number":
                        setattr(existing, key, val)
                existing.updated_at = datetime.now(timezone.utc)
            else:
                firm = Firm(**{k: v for k, v in firm_data.items() if hasattr(Firm, k)})
                db.add(firm)

            db.commit()

            # Disclosures
            db.query(Disclosure).filter(Disclosure.firm_crd == crd).delete()
            raw_disc = raw_adv.get("data", {}).get("disclosures", []) if raw_adv else []
            parsed_disc = parse_disclosures(raw_disc)
            for d in parsed_disc:
                d["firm_crd"] = crd
                db.add(Disclosure(**d))
            db.commit()

            # Holdings + snapshot
            if holdings_data:
                db.query(Holding).filter(Holding.firm_crd == crd).delete()
                for h in holdings_data.get("holdings", []):
                    h["firm_crd"] = crd
                    h["period_end"] = holdings_data.get("period_end")
                    db.add(Holding(**{k: v for k, v in h.items() if hasattr(Holding, k)}))

                snapshot = HoldingSnapshot(
                    firm_crd=crd,
                    period_end=holdings_data.get("period_end"),
                    total_value=holdings_data.get("total_value"),
                    holding_count=holdings_data.get("holding_count"),
                    top10_concentration=holdings_data.get("top10_concentration"),
                    largest_position_pct=holdings_data.get("largest_position_pct"),
                )
                db.add(snapshot)
                db.commit()

            # Change detection
            changes = []
            if prev_dict:
                curr_firm = db.query(Firm).filter(Firm.crd_number == crd).first()
                changes = detect_changes(prev_dict, curr_firm.to_dict())
                for c in changes:
                    c["firm_crd"] = crd
                    db.add(ChangeEvent(**c))
                db.commit()

            # Risk flags
            db.query(RiskFlag).filter(RiskFlag.firm_crd == crd).delete()
            curr_firm = db.query(Firm).filter(Firm.crd_number == crd).first()
            flags = generate_flags(curr_firm.to_dict(), changes, holdings_data or {})
            for f in flags:
                f["firm_crd"] = crd
                db.add(RiskFlag(**{k: v for k, v in f.items() if hasattr(RiskFlag, k)}))
            db.commit()

            # Validate
            field_count = _count_populated(firm_data)
            source = firm_data.get("data_source", "UNKNOWN")
            status = "PASS" if field_count >= 10 else "WARN"
            print(f"    [{status}] {name}: {field_count}/{len(VALIDATION_FIELDS)} fields populated (source: {source})")

            if field_count < 10:
                failures.append(name)

        if failures:
            print(f"  WARNING: Low data coverage for: {', '.join(failures)} (continuing anyway)")

        print(f"  Seeding complete: {len(SEED_FIRMS)} firms loaded.")

    finally:
        if close_db:
            db.close()
