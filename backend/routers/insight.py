import json
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from db.models import get_db, Firm, Disclosure, ChangeEvent
from ai.summary import stream_summary

router = APIRouter()


@router.post("/insight/{crd}")
async def insight(crd: str, db: Session = Depends(get_db)):
    firm = db.query(Firm).filter(Firm.crd_number == crd).first()
    if not firm:
        raise HTTPException(status_code=404, detail="Firm not found")

    disclosures = db.query(Disclosure).filter(Disclosure.firm_crd == crd).all()
    changes = (
        db.query(ChangeEvent)
        .filter(ChangeEvent.firm_crd == crd)
        .order_by(ChangeEvent.created_at.desc())
        .limit(20)
        .all()
    )

    firm_dict = firm.to_dict()
    disc_list = [d.to_dict() for d in disclosures]
    changes_list = [c.to_dict() for c in changes]

    async def event_generator():
        try:
            async for chunk in stream_summary(firm_dict, changes_list, disc_list):
                data = json.dumps({"text": chunk})
                yield f"data: {data}\n\n"
            yield "data: [DONE]\n\n"
        except Exception as e:
            error_data = json.dumps({"error": str(e)})
            yield f"data: {error_data}\n\n"
            yield "data: [DONE]\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )
