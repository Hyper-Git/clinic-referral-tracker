"""The web app: routes for the board, add form, status update and /health."""
import logging
import re
import time
from contextlib import asynccontextmanager
from datetime import date
from pathlib import Path

from fastapi import Depends, FastAPI, Form, HTTPException, Request
from fastapi.responses import JSONResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy import select
from sqlalchemy.orm import Session

import database
from config import settings
from logging_config import setup_logging
from models import PRIORITIES, STATUSES, Referral

setup_logging(settings.log_level)
log = logging.getLogger("referral_tracker")

TEMPLATES = Jinja2Templates(directory=Path(__file__).parent / "templates")
REFERENCE_PATTERN = re.compile(r"^SYN-\d{4,8}$")  # synthetic references only
STARTUP_ATTEMPTS = 5
STARTUP_RETRY_SECONDS = 2


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Create tables on startup, retrying briefly in case the database is still starting.
    for attempt in range(1, STARTUP_ATTEMPTS + 1):
        try:
            database.create_tables()
            log.info("tables ready", extra={"event": "startup_tables_ready"})
            break
        except Exception as exc:
            log.warning("database not ready", extra={
                "event": "startup_db_unavailable", "attempt": attempt, "error": type(exc).__name__})
            if attempt == STARTUP_ATTEMPTS:
                log.error("giving up on database", extra={"event": "startup_failed"})
                raise
            time.sleep(STARTUP_RETRY_SECONDS)
    log.info("app started", extra={"event": "app_started"})
    yield
    log.info("app stopping", extra={"event": "app_stopping"})


app = FastAPI(title="Clinic Referral Tracker", lifespan=lifespan)


@app.middleware("http")
async def log_requests(request: Request, call_next):
    start = time.perf_counter()
    response = await call_next(request)
    # Path only (no query string or form body), so no referral details reach the logs.
    log.info("request", extra={
        "event": "http_request",
        "method": request.method,
        "path": request.url.path,
        "status_code": response.status_code,
        "duration_ms": round((time.perf_counter() - start) * 1000, 1),
    })
    return response


def threshold_for(priority: str) -> int:
    return settings.urgent_threshold_days if priority == "urgent" else settings.routine_threshold_days


def board_rows(referrals: list[Referral], today: date) -> list[dict]:
    rows = []
    for r in referrals:
        days = (today - r.date_received).days
        rows.append({
            "referral": r,
            "days_waiting": days,
            "overdue": r.status != "seen" and days > threshold_for(r.priority),
        })
    # Urgent first, then longest wait first.
    rows.sort(key=lambda row: (row["referral"].priority != "urgent", -row["days_waiting"]))
    return rows


@app.get("/")
def board(request: Request, db: Session = Depends(database.get_db)):
    referrals = list(db.scalars(select(Referral)))
    rows = board_rows(referrals, date.today())
    return TEMPLATES.TemplateResponse(request, "board.html", {
        "rows": rows,
        "overdue_count": sum(1 for row in rows if row["overdue"]),
        "urgent_threshold": settings.urgent_threshold_days,
        "routine_threshold": settings.routine_threshold_days,
    })


@app.get("/referrals/new")
def new_referral_form(request: Request):
    return TEMPLATES.TemplateResponse(request, "new.html", {
        "priorities": PRIORITIES, "errors": [], "form": {"date_received": date.today().isoformat()},
    })


@app.post("/referrals/new")
def create_referral(
    request: Request,
    reference: str = Form(""),
    referring_practice: str = Form(""),
    priority: str = Form(""),
    date_received: str = Form(""),
    db: Session = Depends(database.get_db),
):
    reference = reference.strip().upper()
    referring_practice = referring_practice.strip()
    errors = []
    if not REFERENCE_PATTERN.match(reference):
        errors.append("Reference must be synthetic, in the form SYN-1234.")
    elif db.scalar(select(Referral.id).where(Referral.reference == reference)) is not None:
        errors.append("That reference already exists.")
    if not referring_practice or len(referring_practice) > 120:
        errors.append("Referring practice is required (max 120 characters).")
    if priority not in PRIORITIES:
        errors.append("Priority must be urgent or routine.")
    received = None
    try:
        received = date.fromisoformat(date_received)
        if received > date.today():
            errors.append("Date received can't be in the future.")
    except ValueError:
        errors.append("Date received must be a valid date.")

    if errors:
        return TEMPLATES.TemplateResponse(request, "new.html", {
            "priorities": PRIORITIES,
            "errors": errors,
            "form": {"reference": reference, "referring_practice": referring_practice,
                     "priority": priority, "date_received": date_received},
        }, status_code=400)

    referral = Referral(reference=reference, referring_practice=referring_practice,
                        priority=priority, status="received", date_received=received)
    db.add(referral)
    db.commit()
    log.info("referral created", extra={
        "event": "referral_created", "referral_id": referral.id, "priority": priority})
    return RedirectResponse("/", status_code=303)


def _get_referral(db: Session, referral_id: int) -> Referral:
    referral = db.get(Referral, referral_id)
    if referral is None:
        raise HTTPException(status_code=404, detail="Referral not found")
    return referral


@app.get("/referrals/{referral_id}")
def edit_status_form(referral_id: int, request: Request, db: Session = Depends(database.get_db)):
    referral = _get_referral(db, referral_id)
    return TEMPLATES.TemplateResponse(request, "edit.html", {
        "referral": referral, "statuses": STATUSES, "errors": []})


@app.post("/referrals/{referral_id}/status")
def update_status(
    referral_id: int,
    request: Request,
    status: str = Form(""),
    db: Session = Depends(database.get_db),
):
    referral = _get_referral(db, referral_id)
    if status not in STATUSES:
        return TEMPLATES.TemplateResponse(request, "edit.html", {
            "referral": referral, "statuses": STATUSES,
            "errors": ["Choose a valid status."]}, status_code=400)
    old_status = referral.status
    referral.status = status
    db.commit()
    log.info("referral status updated", extra={
        "event": "referral_status_updated", "referral_id": referral.id,
        "old_status": old_status, "new_status": status})
    return RedirectResponse("/", status_code=303)


@app.get("/health")
def health():
    if database.database_is_reachable():
        return {"status": "ok"}
    log.warning("health check failed", extra={"event": "health_db_unreachable"})
    return JSONResponse({"status": "unavailable", "database": "unreachable"}, status_code=503)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host=settings.app_host, port=settings.app_port, log_config=None)
