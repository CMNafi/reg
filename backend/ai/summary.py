import os
import anthropic

ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
MODEL = "claude-sonnet-4-20250514"


def _get_client():
    return anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)


def _fmt_aum(val):
    if not val:
        return "Not disclosed"
    if val >= 1e12:
        return f"${val/1e12:.1f}T"
    if val >= 1e9:
        return f"${val/1e9:.1f}B"
    if val >= 1e6:
        return f"${val/1e6:.0f}M"
    return f"${val:,.0f}"


def build_prompt(firm: dict, changes: list = None, disclosures: list = None) -> str:
    changes = changes or []
    disclosures = disclosures or []

    name = firm.get("legal_name", "Unknown")
    crd = firm.get("crd_number", "N/A")
    aum_total = _fmt_aum(firm.get("aum_total"))
    aum_disc = _fmt_aum(firm.get("aum_discretionary"))
    city = firm.get("city", "Not disclosed")
    state = firm.get("state", "Not disclosed")
    location = f"{city}, {state}" if city and state else city or state or "Not disclosed"
    emp = firm.get("employee_count")
    clients = firm.get("client_count")
    ownership = firm.get("ownership_structure", "Not disclosed")
    strategy = firm.get("primary_strategy", "Not disclosed")
    custodians = firm.get("custodians") or []
    auditors = firm.get("auditors") or []
    reg_date = firm.get("registration_date", "Not disclosed")
    source = firm.get("data_source", "Unknown")

    aum_per_emp = ""
    if firm.get("aum_total") and emp and emp > 0:
        ape = firm["aum_total"] / emp
        aum_per_emp = f"\n- AUM per Employee: {_fmt_aum(ape)}"

    changes_text = "None recorded."
    if changes:
        lines = []
        for c in changes[:10]:
            lines.append(f"  - [{c.get('materiality', 'N/A')}] {c.get('description', 'N/A')} ({c.get('filing_date', '')})")
        changes_text = "\n".join(lines)

    disc_text = "No disclosures on file."
    if disclosures:
        lines = []
        for d in disclosures[:10]:
            lines.append(f"  - [{d.get('disclosure_type', 'N/A')}] {d.get('description', 'N/A')[:200]} ({d.get('event_date', '')})")
        disc_text = "\n".join(lines)

    return f"""You are a regulatory intelligence analyst. Analyze this SEC-registered investment adviser and produce a factual summary.

FIRM DATA:
- Name: {name}
- CRD Number: {crd}
- Total AUM: {aum_total}
- Discretionary AUM: {aum_disc}
- Location: {location}
- Employees: {emp or 'Not disclosed'}{aum_per_emp}
- Clients: {clients or 'Not disclosed'}
- Ownership: {ownership}
- Strategy: {strategy}
- Custodians: {', '.join(custodians) if custodians else 'Not disclosed'}
- Auditors: {', '.join(auditors) if auditors else 'Not disclosed'}
- SEC Registration Date: {reg_date}
- Data Source: {source}

RECENT CHANGES:
{changes_text}

DISCLOSURES:
{disc_text}

Respond in EXACTLY this structure:

OVERVIEW
2-3 sentences summarizing the firm's profile and regulatory standing.

KEY FACTS
- Fact 1
- Fact 2
- Fact 3
- Fact 4

INVESTOR CONSIDERATIONS
- Consideration 1
- Consideration 2
- Consideration 3

DUE DILIGENCE QUESTIONS
1. Question 1
2. Question 2
3. Question 3
4. Question 4

RULES:
- Be factual only. Do not invent or assume data not provided above.
- If a data point is missing, say "Not disclosed" rather than guessing.
- No marketing language. Be neutral and analytical.
- Focus on what matters to an institutional investor or allocator."""


async def stream_summary(firm: dict, changes: list = None, disclosures: list = None):
    client = _get_client()
    prompt = build_prompt(firm, changes, disclosures)

    with client.messages.stream(
        model=MODEL,
        max_tokens=1500,
        messages=[{"role": "user", "content": prompt}],
    ) as stream:
        for text in stream.text_stream:
            yield text


def generate_summary_sync(firm: dict, changes: list = None, disclosures: list = None) -> str:
    client = _get_client()
    prompt = build_prompt(firm, changes, disclosures)

    message = client.messages.create(
        model=MODEL,
        max_tokens=1500,
        messages=[{"role": "user", "content": prompt}],
    )

    return message.content[0].text
