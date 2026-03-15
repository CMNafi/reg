SEVERITY_ORDER = {"CRITICAL": 0, "HIGH": 1, "MEDIUM": 2, "LOW": 3, "INFORMATIONAL": 4}


def generate_flags(firm_dict: dict, changes_list: list = None, holdings_dict: dict = None) -> list:
    flags = []
    if not firm_dict:
        return flags

    changes_list = changes_list or []
    holdings_dict = holdings_dict or {}

    # --- COMPLIANCE flags ---
    if firm_dict.get("has_criminal_drp"):
        flags.append({
            "category": "COMPLIANCE",
            "severity": "CRITICAL",
            "title": "Criminal Disclosure on Record",
            "description": "This firm has one or more criminal disclosures (DRPs) on file with the SEC.",
            "why_it_matters": "Criminal disclosures may indicate serious misconduct and warrant enhanced due diligence.",
            "evidence": f"DRP count: {firm_dict.get('drp_count', 0)}",
            "is_active": True,
        })
    elif firm_dict.get("has_regulatory_drp"):
        flags.append({
            "category": "COMPLIANCE",
            "severity": "HIGH",
            "title": "Regulatory Disclosure on Record",
            "description": "This firm has regulatory disclosures but no criminal DRPs.",
            "why_it_matters": "Regulatory actions may indicate compliance weaknesses or past violations.",
            "evidence": f"DRP count: {firm_dict.get('drp_count', 0)}",
            "is_active": True,
        })
    elif firm_dict.get("drp_count", 0) > 0:
        flags.append({
            "category": "COMPLIANCE",
            "severity": "MEDIUM",
            "title": "Civil/Financial Disclosure on Record",
            "description": "This firm has civil or financial disclosures on file.",
            "why_it_matters": "While less severe than criminal or regulatory actions, these disclosures should be reviewed.",
            "evidence": f"DRP count: {firm_dict.get('drp_count', 0)}",
            "is_active": True,
        })

    # --- GOVERNANCE flags (from changes) ---
    for change in changes_list:
        ct = change.get("change_type", "")
        if ct == "CUSTODIAN_CHANGE":
            flags.append({
                "category": "GOVERNANCE",
                "severity": "HIGH",
                "title": "Custodian Change Detected",
                "description": change.get("description", "Custodian has changed."),
                "why_it_matters": "Unexpected custodian changes can signal operational instability or disputes with service providers.",
                "evidence": f"Previous: {change.get('previous_value', 'N/A')} → New: {change.get('new_value', 'N/A')}",
                "is_active": True,
            })
        elif ct == "AUDITOR_CHANGE":
            flags.append({
                "category": "GOVERNANCE",
                "severity": "HIGH",
                "title": "Auditor Change Detected",
                "description": change.get("description", "Auditor has changed."),
                "why_it_matters": "Auditor changes may indicate disagreements over financial reporting or compliance concerns.",
                "evidence": f"Previous: {change.get('previous_value', 'N/A')} → New: {change.get('new_value', 'N/A')}",
                "is_active": True,
            })
        elif ct == "OWNERSHIP_CHANGE":
            flags.append({
                "category": "GOVERNANCE",
                "severity": "MEDIUM",
                "title": "Ownership Structure Changed",
                "description": change.get("description", "Ownership structure has changed."),
                "why_it_matters": "Changes in ownership may affect investment strategy, team stability, or regulatory status.",
                "evidence": f"Previous: {change.get('previous_value', 'N/A')} → New: {change.get('new_value', 'N/A')}",
                "is_active": True,
            })

    # --- OPERATIONAL flags ---
    emp = firm_dict.get("employee_count")
    emp_prior = firm_dict.get("employee_count_prior")
    if emp is not None and emp_prior is not None and emp_prior > 0:
        pct = (emp_prior - emp) / emp_prior * 100
        if pct > 35:
            flags.append({
                "category": "OPERATIONAL",
                "severity": "HIGH",
                "title": "Significant Employee Decline",
                "description": f"Employee count dropped {pct:.0f}% from {emp_prior} to {emp}.",
                "why_it_matters": "Large staff reductions may indicate financial distress, loss of key personnel, or operational downsizing.",
                "evidence": f"Prior: {emp_prior}, Current: {emp}",
                "is_active": True,
            })
        elif pct > 20:
            flags.append({
                "category": "OPERATIONAL",
                "severity": "MEDIUM",
                "title": "Notable Employee Decline",
                "description": f"Employee count dropped {pct:.0f}% from {emp_prior} to {emp}.",
                "why_it_matters": "Staff reductions should be monitored for potential impact on service quality.",
                "evidence": f"Prior: {emp_prior}, Current: {emp}",
                "is_active": True,
            })

    aum = firm_dict.get("aum_total")
    for change in changes_list:
        if change.get("field_name") == "aum_total":
            prev_aum = float(change.get("previous_value", 0) or 0)
            curr_aum = float(change.get("new_value", 0) or 0)
            if prev_aum > 0:
                pct = (prev_aum - curr_aum) / prev_aum * 100
                if pct > 30:
                    flags.append({
                        "category": "OPERATIONAL",
                        "severity": "HIGH",
                        "title": "Significant AUM Decline",
                        "description": f"AUM decreased by {pct:.0f}%.",
                        "why_it_matters": "May indicate client redemptions or mandate loss.",
                        "evidence": f"Previous AUM: ${prev_aum:,.0f}, Current: ${curr_aum:,.0f}",
                        "is_active": True,
                    })
                elif pct < -50:
                    flags.append({
                        "category": "OPERATIONAL",
                        "severity": "INFORMATIONAL",
                        "title": "Rapid AUM Growth",
                        "description": f"AUM grew by {abs(pct):.0f}%.",
                        "why_it_matters": "Confirm operational infrastructure scaled accordingly.",
                        "evidence": f"Previous AUM: ${prev_aum:,.0f}, Current: ${curr_aum:,.0f}",
                        "is_active": True,
                    })

    # --- HOLDINGS flags ---
    top10 = holdings_dict.get("top10_concentration")
    if top10 is not None:
        if top10 > 70:
            flags.append({
                "category": "HOLDINGS",
                "severity": "HIGH",
                "title": "High Portfolio Concentration",
                "description": f"Top 10 holdings represent {top10:.1f}% of the portfolio.",
                "why_it_matters": "Highly concentrated portfolios carry elevated idiosyncratic risk.",
                "evidence": f"Top 10 concentration: {top10:.1f}%",
                "is_active": True,
            })
        elif top10 > 50:
            flags.append({
                "category": "HOLDINGS",
                "severity": "MEDIUM",
                "title": "Moderate Portfolio Concentration",
                "description": f"Top 10 holdings represent {top10:.1f}% of the portfolio.",
                "why_it_matters": "Portfolio concentration is above average and should be monitored.",
                "evidence": f"Top 10 concentration: {top10:.1f}%",
                "is_active": True,
            })

    largest = holdings_dict.get("largest_position_pct")
    if largest is not None:
        if largest > 20:
            flags.append({
                "category": "HOLDINGS",
                "severity": "HIGH",
                "title": "Outsized Single Position",
                "description": f"Largest position represents {largest:.1f}% of the portfolio.",
                "why_it_matters": "A single position exceeding 20% creates significant concentration risk.",
                "evidence": f"Largest position: {largest:.1f}%",
                "is_active": True,
            })
        elif largest > 15:
            flags.append({
                "category": "HOLDINGS",
                "severity": "MEDIUM",
                "title": "Large Single Position",
                "description": f"Largest position represents {largest:.1f}% of the portfolio.",
                "why_it_matters": "Single positions above 15% warrant monitoring for concentration risk.",
                "evidence": f"Largest position: {largest:.1f}%",
                "is_active": True,
            })

    flags.sort(key=lambda f: SEVERITY_ORDER.get(f.get("severity", "LOW"), 3))
    return flags
