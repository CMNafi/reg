import os

try:
    from edgar import set_identity, Company
    identity = os.getenv("SEC_USER_AGENT", "RegIntel admin@example.com")
    set_identity(identity)
    EDGAR_AVAILABLE = True
except Exception:
    EDGAR_AVAILABLE = False


def get_13f_holdings(cik: str) -> dict | None:
    if not EDGAR_AVAILABLE or not cik:
        return None

    try:
        company = Company(cik)
        filings = company.get_filings(form="13F-HR")
        if not filings or len(filings) == 0:
            return None

        latest = filings.latest()
        if not latest:
            return None

        obj = latest.obj()
        if not hasattr(obj, "holdings"):
            return None

        df = obj.holdings
        if df is None or len(df) == 0:
            return None

        if hasattr(df, "to_pandas"):
            df = df.to_pandas()

        value_col = None
        for col_name in ["value", "Value", "market_value", "VALUE", "marketValue"]:
            if col_name in df.columns:
                value_col = col_name
                break

        if value_col is None:
            for col in df.columns:
                if "value" in str(col).lower() or "val" in str(col).lower():
                    value_col = col
                    break

        if value_col is None:
            value_col = df.columns[0]

        df = df.sort_values(by=value_col, ascending=False)

        total_value = float(df[value_col].sum())

        df["weight"] = (df[value_col] / total_value * 100).round(2) if total_value > 0 else 0

        holding_count = len(df)

        top10_vals = df.head(10)[value_col].sum()
        top10_concentration = round(top10_vals / total_value * 100, 2) if total_value > 0 else 0

        largest_pct = round(float(df.iloc[0][value_col]) / total_value * 100, 2) if total_value > 0 and len(df) > 0 else 0

        name_col = None
        for col_name in ["nameOfIssuer", "issuer", "name", "Issuer", "Name", "issuer_name"]:
            if col_name in df.columns:
                name_col = col_name
                break
        if name_col is None:
            name_col = df.columns[1] if len(df.columns) > 1 else df.columns[0]

        cusip_col = None
        for col_name in ["cusip", "CUSIP", "Cusip"]:
            if col_name in df.columns:
                cusip_col = col_name
                break

        shares_col = None
        for col_name in ["shares", "Shares", "shrsOrPrnAmt", "quantity", "Quantity"]:
            if col_name in df.columns:
                shares_col = col_name
                break

        ticker_col = None
        for col_name in ["ticker", "Ticker", "symbol", "Symbol"]:
            if col_name in df.columns:
                ticker_col = col_name
                break

        period_end = None
        if hasattr(latest, "period_of_report"):
            period_end = str(latest.period_of_report)
        elif hasattr(latest, "filing_date"):
            period_end = str(latest.filing_date)

        top_25 = df.head(25)
        holdings_list = []
        for _, row in top_25.iterrows():
            h = {
                "issuer_name": str(row.get(name_col, "")) if name_col else "",
                "cusip": str(row.get(cusip_col, "")) if cusip_col else "",
                "ticker": str(row.get(ticker_col, "")) if ticker_col else "",
                "market_value": float(row.get(value_col, 0)),
                "shares": float(row.get(shares_col, 0)) if shares_col and row.get(shares_col) else 0,
                "weight": float(row.get("weight", 0)),
                "is_new": False,
                "is_exited": False,
            }
            holdings_list.append(h)

        return {
            "period_end": period_end,
            "total_value": total_value,
            "holding_count": holding_count,
            "top10_concentration": top10_concentration,
            "largest_position_pct": largest_pct,
            "holdings": holdings_list,
        }

    except Exception as e:
        print(f"  [13F] Error fetching holdings for CIK {cik}: {e}")
        return None


def get_filing_history(cik: str) -> list:
    if not EDGAR_AVAILABLE or not cik:
        return []

    try:
        company = Company(cik)
        results = []

        for form_type in ["ADV", "13F-HR"]:
            try:
                filings = company.get_filings(form=form_type)
                if filings:
                    for f in list(filings)[:10]:
                        results.append({
                            "form_type": form_type,
                            "filing_date": str(getattr(f, "filing_date", "")),
                            "period": str(getattr(f, "period_of_report", "")),
                            "is_amendment": "A" in str(getattr(f, "form", "")),
                        })
            except Exception:
                continue

        return sorted(results, key=lambda x: x.get("filing_date", ""), reverse=True)

    except Exception:
        return []
