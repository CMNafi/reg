import os
import httpx
from datetime import datetime, timezone

SEC_USER_AGENT = os.getenv("SEC_USER_AGENT", "RegIntel admin@example.com")
IAPD_BASE = "https://api.adviserinfo.sec.gov"
EDGAR_SEARCH = "https://efts.sec.gov/LATEST/search-index"


async def get_adv_by_crd(crd: str) -> dict | None:
    headers = {"User-Agent": SEC_USER_AGENT, "Accept": "application/json"}
    async with httpx.AsyncClient(timeout=30) as client:
        try:
            resp = await client.get(f"{IAPD_BASE}/IAPD/content/viewform/adv/{crd}", headers=headers)
            if resp.status_code == 200:
                data = resp.json()
                return {"data": data, "source": "SEC_IAPD"}
        except Exception:
            pass

        try:
            resp = await client.get(
                f"{IAPD_BASE}/search/firm",
                params={"query": crd, "nrows": 1},
                headers=headers
            )
            if resp.status_code == 200:
                data = resp.json()
                hits = data.get("hits", data.get("results", []))
                if isinstance(hits, dict):
                    hits = hits.get("hits", [])
                if hits:
                    return {"data": hits[0] if isinstance(hits, list) else hits, "source": "SEC_IAPD"}
        except Exception:
            pass

        try:
            resp = await client.get(
                EDGAR_SEARCH,
                params={"q": f'"{crd}"', "forms": "ADV"},
                headers=headers
            )
            if resp.status_code == 200:
                data = resp.json()
                return {"data": data, "source": "EDGAR_SEARCH"}
        except Exception:
            pass

    return None


def normalize_iapd(raw: dict) -> dict:
    if not raw:
        return {}

    data = raw.get("data", raw)
    source = raw.get("source", "SEC_IAPD")

    basic = data.get("basicInformation", data.get("basic_information", {}))
    if not basic:
        basic = data

    assets = data.get("regulatoryAssets", data.get("regulatory_assets", {}))
    if not assets:
        assets = data

    office = data.get("principalOfficeAddress", data.get("principal_office_address", {}))
    if not office:
        office = data

    disclosures_data = data.get("disclosures", [])

    crd = str(basic.get("crdNumber", basic.get("crd_number", basic.get("crd", ""))))
    legal_name = basic.get("legalName", basic.get("legal_name", basic.get("firmName", basic.get("firm_name", ""))))
    dba = basic.get("doingBusinessAs", basic.get("doing_business_as", basic.get("dba", "")))

    aum_total = assets.get("totalAssetsUnderManagement", assets.get("total_assets", assets.get("aum_total", None)))
    aum_disc = assets.get("discretionaryAssetsUnderManagement", assets.get("discretionary_assets", assets.get("aum_discretionary", None)))

    if isinstance(aum_total, str):
        aum_total = float(aum_total.replace(",", "").replace("$", "")) if aum_total else None
    if isinstance(aum_disc, str):
        aum_disc = float(aum_disc.replace(",", "").replace("$", "")) if aum_disc else None

    city = office.get("city", office.get("City", ""))
    state = office.get("state", office.get("State", office.get("stateCode", "")))
    country = office.get("country", office.get("Country", "US"))

    emp = basic.get("numberOfEmployees", basic.get("employee_count", basic.get("totalEmployees", None)))
    if isinstance(emp, str):
        emp = int(emp) if emp.isdigit() else None

    clients = basic.get("numberOfClients", basic.get("client_count", None))
    if isinstance(clients, str):
        clients = int(clients) if clients.isdigit() else None

    reg_date = basic.get("registrationDate", basic.get("registration_date", basic.get("secRegistrationDate", "")))
    website = basic.get("website", basic.get("Website", basic.get("firmWebsite", "")))

    drp_count = 0
    has_criminal = False
    has_regulatory = False
    if isinstance(disclosures_data, list):
        drp_count = len(disclosures_data)
        for d in disclosures_data:
            dtype = str(d.get("disclosureType", d.get("disclosure_type", ""))).lower()
            if "criminal" in dtype:
                has_criminal = True
            if "regulatory" in dtype:
                has_regulatory = True

    ownership = basic.get("ownershipStructure", basic.get("ownership_structure",
                basic.get("formOfOrganization", "")))
    strategy = basic.get("primaryStrategy", basic.get("primary_strategy", ""))
    fee_structure = basic.get("feeStructure", basic.get("fee_structure", ""))
    private_funds = basic.get("numberOfPrivateFunds", basic.get("private_fund_count", None))
    if isinstance(private_funds, str):
        private_funds = int(private_funds) if private_funds.isdigit() else None

    custodians = basic.get("custodians", data.get("custodians", []))
    if isinstance(custodians, str):
        custodians = [custodians] if custodians else []

    auditors = basic.get("auditors", data.get("auditors", []))
    if isinstance(auditors, str):
        auditors = [auditors] if auditors else []

    return {
        "crd_number": crd,
        "legal_name": legal_name or None,
        "doing_business_as": dba or None,
        "registration_date": reg_date or None,
        "last_adv_date": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
        "aum_total": aum_total,
        "aum_discretionary": aum_disc,
        "employee_count": emp,
        "client_count": clients,
        "private_fund_count": private_funds,
        "city": city or None,
        "state": state or None,
        "country": country or "US",
        "website": website or None,
        "primary_strategy": strategy or None,
        "ownership_structure": ownership or None,
        "fee_structure": fee_structure or None,
        "drp_count": drp_count,
        "has_criminal_drp": has_criminal,
        "has_regulatory_drp": has_regulatory,
        "custodians": custodians if custodians else None,
        "auditors": auditors if auditors else None,
        "data_source": source,
        "data_verified_at": datetime.now(timezone.utc).isoformat(),
        "raw_adv": data,
    }


def parse_disclosures(raw_disclosures: list) -> list:
    results = []
    if not isinstance(raw_disclosures, list):
        return results

    for d in raw_disclosures:
        dtype = d.get("disclosureType", d.get("disclosure_type", d.get("type", "")))
        if str(dtype).lower() == "none" or not dtype:
            continue

        event_date = d.get("eventDate", d.get("event_date", d.get("date", "")))
        description = d.get("description", d.get("disclosureDetail", d.get("details", "")))
        resolution = d.get("resolution", d.get("resolutionDetail", ""))
        is_resolved = bool(resolution) or str(d.get("status", "")).lower() in ("resolved", "closed")

        results.append({
            "disclosure_type": dtype,
            "event_date": event_date or None,
            "description": description or None,
            "resolution": resolution or None,
            "is_resolved": is_resolved,
        })

    return results


async def search_firms_by_name(name: str, limit: int = 20) -> list:
    headers = {"User-Agent": SEC_USER_AGENT, "Accept": "application/json"}
    async with httpx.AsyncClient(timeout=30) as client:
        try:
            resp = await client.get(
                f"{IAPD_BASE}/search/firm",
                params={"query": name, "nrows": limit},
                headers=headers
            )
            if resp.status_code == 200:
                data = resp.json()
                hits = data.get("hits", data.get("results", []))
                if isinstance(hits, dict):
                    hits = hits.get("hits", [])
                return hits if isinstance(hits, list) else []
        except Exception:
            pass
    return []
