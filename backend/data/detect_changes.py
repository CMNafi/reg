import json
from datetime import datetime, timezone


def detect_changes(prev_dict: dict, curr_dict: dict, filing_date: str = None) -> list:
    if not prev_dict or not curr_dict:
        return []

    if not filing_date:
        filing_date = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    changes = []

    # AUM total
    prev_aum = prev_dict.get("aum_total")
    curr_aum = curr_dict.get("aum_total")
    if prev_aum and curr_aum and prev_aum > 0:
        pct_change = abs(curr_aum - prev_aum) / prev_aum * 100
        if pct_change > 10:
            materiality = "HIGH" if pct_change > 30 else "MEDIUM"
            direction = "increased" if curr_aum > prev_aum else "decreased"
            changes.append({
                "filing_date": filing_date,
                "field_name": "aum_total",
                "previous_value": str(prev_aum),
                "new_value": str(curr_aum),
                "change_type": "AUM_CHANGE",
                "description": f"AUM {direction} by {pct_change:.1f}%",
                "materiality": materiality,
            })

    # Employee count
    prev_emp = prev_dict.get("employee_count")
    curr_emp = curr_dict.get("employee_count")
    if prev_emp is not None and curr_emp is not None and prev_emp != curr_emp and prev_emp > 0:
        pct_change = abs(curr_emp - prev_emp) / prev_emp * 100
        direction = "increased" if curr_emp > prev_emp else "decreased"
        materiality = "HIGH" if (curr_emp < prev_emp and pct_change > 35) else "MEDIUM"
        changes.append({
            "filing_date": filing_date,
            "field_name": "employee_count",
            "previous_value": str(prev_emp),
            "new_value": str(curr_emp),
            "change_type": "EMPLOYEE_CHANGE",
            "description": f"Employee count {direction} from {prev_emp} to {curr_emp} ({pct_change:.1f}%)",
            "materiality": materiality,
        })

    # DRP count
    prev_drp = prev_dict.get("drp_count", 0)
    curr_drp = curr_dict.get("drp_count", 0)
    if curr_drp > prev_drp:
        changes.append({
            "filing_date": filing_date,
            "field_name": "drp_count",
            "previous_value": str(prev_drp),
            "new_value": str(curr_drp),
            "change_type": "DRP_INCREASE",
            "description": f"Disclosure count increased from {prev_drp} to {curr_drp}",
            "materiality": "HIGH",
        })

    # City
    prev_city = prev_dict.get("city", "")
    curr_city = curr_dict.get("city", "")
    if prev_city and curr_city and prev_city != curr_city:
        changes.append({
            "filing_date": filing_date,
            "field_name": "city",
            "previous_value": prev_city,
            "new_value": curr_city,
            "change_type": "LOCATION_CHANGE",
            "description": f"City changed from {prev_city} to {curr_city}",
            "materiality": "MEDIUM",
        })

    # State
    prev_state = prev_dict.get("state", "")
    curr_state = curr_dict.get("state", "")
    if prev_state and curr_state and prev_state != curr_state:
        changes.append({
            "filing_date": filing_date,
            "field_name": "state",
            "previous_value": prev_state,
            "new_value": curr_state,
            "change_type": "LOCATION_CHANGE",
            "description": f"State changed from {prev_state} to {curr_state}",
            "materiality": "MEDIUM",
        })

    # Ownership structure
    prev_own = prev_dict.get("ownership_structure", "")
    curr_own = curr_dict.get("ownership_structure", "")
    if prev_own and curr_own and prev_own != curr_own:
        changes.append({
            "filing_date": filing_date,
            "field_name": "ownership_structure",
            "previous_value": prev_own,
            "new_value": curr_own,
            "change_type": "OWNERSHIP_CHANGE",
            "description": f"Ownership structure changed from '{prev_own}' to '{curr_own}'",
            "materiality": "MEDIUM",
        })

    # Custodians
    prev_cust = set(_to_list(prev_dict.get("custodians")))
    curr_cust = set(_to_list(curr_dict.get("custodians")))
    if prev_cust and curr_cust and prev_cust != curr_cust:
        added = curr_cust - prev_cust
        removed = prev_cust - curr_cust
        parts = []
        if added:
            parts.append(f"Added: {', '.join(added)}")
        if removed:
            parts.append(f"Removed: {', '.join(removed)}")
        changes.append({
            "filing_date": filing_date,
            "field_name": "custodians",
            "previous_value": json.dumps(list(prev_cust)),
            "new_value": json.dumps(list(curr_cust)),
            "change_type": "CUSTODIAN_CHANGE",
            "description": f"Custodian changes: {'; '.join(parts)}",
            "materiality": "HIGH",
        })

    # Auditors
    prev_aud = set(_to_list(prev_dict.get("auditors")))
    curr_aud = set(_to_list(curr_dict.get("auditors")))
    if prev_aud and curr_aud and prev_aud != curr_aud:
        added = curr_aud - prev_aud
        removed = prev_aud - curr_aud
        parts = []
        if added:
            parts.append(f"Added: {', '.join(added)}")
        if removed:
            parts.append(f"Removed: {', '.join(removed)}")
        changes.append({
            "filing_date": filing_date,
            "field_name": "auditors",
            "previous_value": json.dumps(list(prev_aud)),
            "new_value": json.dumps(list(curr_aud)),
            "change_type": "AUDITOR_CHANGE",
            "description": f"Auditor changes: {'; '.join(parts)}",
            "materiality": "HIGH",
        })

    return changes


def _to_list(val) -> list:
    if val is None:
        return []
    if isinstance(val, list):
        return [str(v) for v in val if v]
    if isinstance(val, str):
        try:
            parsed = json.loads(val)
            if isinstance(parsed, list):
                return [str(v) for v in parsed if v]
        except Exception:
            pass
        return [val] if val else []
    return []
