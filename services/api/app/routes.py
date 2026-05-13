import csv
import io
from datetime import date, datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from sqlalchemy import func

from .database import get_db
from .models import Reading, Machine, Test, TestReading, TestStatus
from .schemas import (
    ReadingIn, ReadingOut,
    MachineIn, MachineOut,
    TestStart, TestOut, TestSummary,
    TestReadingIn, TestReadingOut,
)
from .auth import verify_api_key

router = APIRouter()


# ── Health ────────────────────────────────────────────────
@router.get("/health")
def health():
    return {"status": "ok"}


# ── Live readings ─────────────────────────────────────────
@router.post("/reading", status_code=201, response_model=ReadingOut,
             dependencies=[Depends(verify_api_key)])
def create_reading(payload: ReadingIn, db: Session = Depends(get_db)):
    row = Reading(device_id=payload.device_id, temperature=payload.temperature)
    db.add(row); db.commit(); db.refresh(row)
    return row

@router.get("/readings", response_model=list[ReadingOut])
def list_readings(device_id: Optional[str] = None, limit: int = 200,
                  db: Session = Depends(get_db)):
    q = db.query(Reading)
    if device_id:
        q = q.filter(Reading.device_id == device_id)
    return q.order_by(Reading.timestamp.desc()).limit(limit).all()

@router.get("/readings/stats")
def readings_stats(device_id: Optional[str] = None, db: Session = Depends(get_db)):
    q = db.query(
        func.min(Reading.temperature).label("min"),
        func.max(Reading.temperature).label("max"),
        func.avg(Reading.temperature).label("avg"),
        func.count(Reading.id).label("count"),
    )
    if device_id:
        q = q.filter(Reading.device_id == device_id)
    row = q.one()
    return {"min": round(float(row.min or 0), 2), "max": round(float(row.max or 0), 2),
            "avg": round(float(row.avg or 0), 2), "count": row.count}

@router.get("/export/csv")
def export_csv(day: str = str(date.today()), device_id: Optional[str] = None,
               db: Session = Depends(get_db)):
    q = db.query(Reading).filter(func.date(Reading.timestamp) == day)
    if device_id:
        q = q.filter(Reading.device_id == device_id)
    rows = q.order_by(Reading.timestamp.asc()).all()
    if not rows:
        raise HTTPException(404, f"No data for {day}")
    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(["id", "device_id", "temperature", "timestamp"])
    for r in rows:
        w.writerow([r.id, r.device_id, float(r.temperature), r.timestamp.isoformat()])
    return StreamingResponse(iter([buf.getvalue()]), media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename=readings_{day}.csv"})


# ── Machines ──────────────────────────────────────────────
@router.post("/machines", status_code=201, response_model=MachineOut,
             dependencies=[Depends(verify_api_key)])
def create_machine(payload: MachineIn, db: Session = Depends(get_db)):
    if db.query(Machine).filter(Machine.name == payload.name).first():
        raise HTTPException(400, "Machine name already exists")
    m = Machine(**payload.model_dump())
    db.add(m); db.commit(); db.refresh(m)
    return m

@router.get("/machines", response_model=list[MachineOut])
def list_machines(db: Session = Depends(get_db)):
    return db.query(Machine).order_by(Machine.name).all()

@router.get("/machines/{machine_id}", response_model=MachineOut)
def get_machine(machine_id: int, db: Session = Depends(get_db)):
    m = db.query(Machine).filter(Machine.id == machine_id).first()
    if not m:
        raise HTTPException(404, "Machine not found")
    return m

@router.put("/machines/{machine_id}", response_model=MachineOut,
            dependencies=[Depends(verify_api_key)])
def update_machine(machine_id: int, payload: MachineIn, db: Session = Depends(get_db)):
    m = db.query(Machine).filter(Machine.id == machine_id).first()
    if not m:
        raise HTTPException(404, "Machine not found")
    for k, v in payload.model_dump().items():
        setattr(m, k, v)
    db.commit(); db.refresh(m)
    return m

@router.delete("/machines/{machine_id}", status_code=204,
               dependencies=[Depends(verify_api_key)])
def delete_machine(machine_id: int, db: Session = Depends(get_db)):
    m = db.query(Machine).filter(Machine.id == machine_id).first()
    if not m:
        raise HTTPException(404, "Machine not found")
    db.delete(m); db.commit()


# ── Tests ─────────────────────────────────────────────────
@router.post("/tests", status_code=201, response_model=TestOut,
             dependencies=[Depends(verify_api_key)])
def start_test(payload: TestStart, db: Session = Depends(get_db)):
    if not db.query(Machine).filter(Machine.id == payload.machine_id).first():
        raise HTTPException(404, "Machine not found")
    t = Test(machine_id=payload.machine_id, type=payload.type,
             reference_channel=payload.reference_channel)
    db.add(t); db.commit(); db.refresh(t)
    return db.query(Test).filter(Test.id == t.id).first()

@router.post("/tests/{test_id}/readings", status_code=201,
             response_model=list[TestReadingOut],
             dependencies=[Depends(verify_api_key)])
def add_test_readings(test_id: int, readings: list[TestReadingIn],
                      db: Session = Depends(get_db)):
    test = db.query(Test).filter(Test.id == test_id).first()
    if not test:
        raise HTTPException(404, "Test not found")
    if test.status != TestStatus.running:
        raise HTTPException(400, "Test is not running")
    now = datetime.now(timezone.utc)
    rows = [TestReading(test_id=test_id, channel=r.channel,
                        value=r.value, unit=r.unit, timestamp=now)
            for r in readings]
    db.add_all(rows); db.commit()
    return rows

@router.post("/tests/{test_id}/finish", response_model=TestOut,
             dependencies=[Depends(verify_api_key)])
def finish_test(test_id: int, db: Session = Depends(get_db)):
    test = db.query(Test).filter(Test.id == test_id).first()
    if not test:
        raise HTTPException(404, "Test not found")
    test.status     = TestStatus.finished
    test.finished_at = datetime.now(timezone.utc)
    db.commit(); db.refresh(test)
    return db.query(Test).filter(Test.id == test_id).first()

@router.get("/tests", response_model=list[TestSummary])
def list_tests(
    type:       Optional[str]  = None,
    status:     Optional[str]  = None,
    date_from:  Optional[str]  = None,
    date_to:    Optional[str]  = None,
    db: Session = Depends(get_db),
):
    q = db.query(Test)
    if type:
        q = q.filter(Test.type == type)
    if status:
        q = q.filter(Test.status == status)
    if date_from:
        q = q.filter(func.date(Test.started_at) >= date_from)
    if date_to:
        q = q.filter(func.date(Test.started_at) <= date_to)
    return q.order_by(Test.started_at.desc()).all()

@router.get("/tests/today", response_model=list[TestSummary])
def tests_today(type: Optional[str] = None, db: Session = Depends(get_db)):
    q = db.query(Test).filter(func.date(Test.started_at) == date.today())
    if type:
        q = q.filter(Test.type == type)
    return q.order_by(Test.started_at.desc()).all()

@router.get("/tests/{test_id}", response_model=TestOut)
def get_test(test_id: int, db: Session = Depends(get_db)):
    t = db.query(Test).filter(Test.id == test_id).first()
    if not t:
        raise HTTPException(404, "Test not found")
    return t
