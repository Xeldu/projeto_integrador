import csv
import io
from datetime import date
from typing import Optional

from fastapi import APIRouter, Depends, Header, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from sqlalchemy import func

from .database import get_db
from .models import Reading
from .schemas import ReadingIn, ReadingOut
from .auth import verify_api_key

router = APIRouter()


@router.post("/reading", status_code=201, response_model=ReadingOut)
def create_reading(
    payload: ReadingIn,
    db: Session = Depends(get_db),
    _: None = Depends(verify_api_key),
):
    row = Reading(device_id=payload.device_id, temperature=payload.temperature)
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


@router.get("/readings", response_model=list[ReadingOut])
def list_readings(
    device_id: Optional[str] = None,
    limit: int = 200,
    db: Session = Depends(get_db),
):
    q = db.query(Reading)
    if device_id:
        q = q.filter(Reading.device_id == device_id)
    return q.order_by(Reading.timestamp.desc()).limit(limit).all()


@router.get("/readings/today", response_model=list[ReadingOut])
def readings_today(
    device_id: Optional[str] = None,
    db: Session = Depends(get_db),
):
    q = db.query(Reading).filter(
        func.date(Reading.timestamp) == date.today()
    )
    if device_id:
        q = q.filter(Reading.device_id == device_id)
    return q.order_by(Reading.timestamp.asc()).all()


@router.get("/readings/stats")
def readings_stats(
    device_id: Optional[str] = None,
    db: Session = Depends(get_db),
):
    q = db.query(
        func.min(Reading.temperature).label("min"),
        func.max(Reading.temperature).label("max"),
        func.avg(Reading.temperature).label("avg"),
        func.count(Reading.id).label("count"),
    )
    if device_id:
        q = q.filter(Reading.device_id == device_id)
    row = q.one()
    return {
        "min":   round(float(row.min  or 0), 2),
        "max":   round(float(row.max  or 0), 2),
        "avg":   round(float(row.avg  or 0), 2),
        "count": row.count,
    }


@router.get("/export/csv")
def export_csv(
    day: str = str(date.today()),
    device_id: Optional[str] = None,
    db: Session = Depends(get_db),
):
    q = db.query(Reading).filter(func.date(Reading.timestamp) == day)
    if device_id:
        q = q.filter(Reading.device_id == device_id)
    rows = q.order_by(Reading.timestamp.asc()).all()

    if not rows:
        raise HTTPException(404, f"No data for {day}")

    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(["id", "device_id", "temperature", "timestamp"])
    for r in rows:
        writer.writerow([r.id, r.device_id, float(r.temperature), r.timestamp.isoformat()])

    return StreamingResponse(
        iter([buf.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename=readings_{day}.csv"},
    )


@router.delete("/readings", status_code=200)
def reset_readings(
    db: Session = Depends(get_db),
    _: None = Depends(verify_api_key),
):
    db.query(Reading).delete()
    db.commit()
    return {"deleted": True}


@router.get("/health")
def health():
    return {"status": "ok"}
