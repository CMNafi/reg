from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from db.models import get_db, Firm

router = APIRouter()


@router.get("/search")
def search_firms(
    q: str = Query(None),
    state: str = Query(None),
    min_aum: float = Query(None),
    max_aum: float = Query(None),
    strategy: str = Query(None),
    has_drp: bool = Query(None),
    limit: int = Query(20, le=100),
    offset: int = Query(0),
    db: Session = Depends(get_db),
):
    query = db.query(Firm)

    if q:
        q_lower = q.strip().lower()
        query = query.filter(
            (Firm.legal_name.ilike(f"%{q_lower}%")) |
            (Firm.doing_business_as.ilike(f"%{q_lower}%")) |
            (Firm.crd_number == q.strip())
        )

    if state:
        query = query.filter(Firm.state.ilike(state.strip()))

    if min_aum is not None:
        query = query.filter(Firm.aum_total >= min_aum)

    if max_aum is not None:
        query = query.filter(Firm.aum_total <= max_aum)

    if strategy:
        query = query.filter(Firm.primary_strategy.ilike(f"%{strategy}%"))

    if has_drp is not None:
        if has_drp:
            query = query.filter(Firm.drp_count > 0)
        else:
            query = query.filter((Firm.drp_count == 0) | (Firm.drp_count.is_(None)))

    total = query.count()

    firms = (
        query
        .order_by(Firm.aum_total.desc().nullslast())
        .offset(offset)
        .limit(limit)
        .all()
    )

    firm_fields = [
        "crd_number", "cik", "legal_name", "doing_business_as", "aum_total",
        "employee_count", "client_count", "city", "state", "primary_strategy",
        "drp_count", "has_criminal_drp", "has_regulatory_drp", "data_source",
        "data_verified_at", "last_adv_date", "last_13f_date", "updated_at",
    ]

    return {
        "firms": [
            {f: getattr(firm, f) for f in firm_fields}
            for firm in firms
        ],
        "total": total,
    }
