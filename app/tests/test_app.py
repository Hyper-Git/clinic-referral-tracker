import json
import logging
from datetime import date, timedelta

import database
from logging_config import JsonFormatter
from main import board_rows
from models import Referral


def add(client, reference="SYN-2001", priority="urgent", days_ago=1, practice="Test Practice"):
    return client.post("/referrals/new", data={
        "reference": reference,
        "referring_practice": practice,
        "priority": priority,
        "date_received": (date.today() - timedelta(days=days_ago)).isoformat(),
    }, follow_redirects=False)


def test_health_ok(client):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_health_returns_503_when_database_unreachable(client, monkeypatch):
    # Point the app at a PostgreSQL server that doesn't exist (port 1 on localhost).
    dead = database.make_engine("postgresql+psycopg://user:pass@127.0.0.1:1/none", connect_timeout=1)
    monkeypatch.setattr(database, "engine", dead)
    response = client.get("/health")
    assert response.status_code == 503


def test_add_referral_shows_on_board(client):
    response = add(client)
    assert response.status_code == 303
    board = client.get("/")
    assert board.status_code == 200
    assert "SYN-2001" in board.text


def test_rejects_non_synthetic_reference(client):
    response = add(client, reference="REAL-123")
    assert response.status_code == 400
    assert "synthetic" in response.text


def test_rejects_duplicate_reference(client):
    add(client)
    assert add(client).status_code == 400


def test_update_status(client):
    add(client)
    with database.SessionLocal() as db:
        referral_id = db.query(Referral).one().id
    response = client.post(f"/referrals/{referral_id}/status", data={"status": "triaged"},
                           follow_redirects=False)
    assert response.status_code == 303
    with database.SessionLocal() as db:
        assert db.get(Referral, referral_id).status == "triaged"


def test_update_status_rejects_invalid_value(client):
    add(client)
    with database.SessionLocal() as db:
        referral_id = db.query(Referral).one().id
    response = client.post(f"/referrals/{referral_id}/status", data={"status": "lost"})
    assert response.status_code == 400


def test_board_sorting_and_overdue_flags():
    today = date.today()

    def r(ref, priority, days, status="received"):
        return Referral(reference=ref, referring_practice="x", priority=priority,
                        status=status, date_received=today - timedelta(days=days))

    rows = board_rows([
        r("SYN-1", "routine", 50),           # routine, over 42 -> overdue
        r("SYN-2", "urgent", 5),             # urgent, under 14
        r("SYN-3", "urgent", 20),            # urgent, over 14 -> overdue
        r("SYN-4", "routine", 10),           # routine, under 42
        r("SYN-5", "urgent", 30, "seen"),    # seen -> never flagged
    ], today)

    assert [row["referral"].reference for row in rows] == ["SYN-5", "SYN-3", "SYN-2", "SYN-1", "SYN-4"]
    flags = {row["referral"].reference: row["overdue"] for row in rows}
    assert flags == {"SYN-1": True, "SYN-2": False, "SYN-3": True, "SYN-4": False, "SYN-5": False}


def test_logs_never_contain_referral_details(client, caplog):
    caplog.set_level(logging.INFO)
    add(client, reference="SYN-9999", practice="Secret Practice Name")
    with database.SessionLocal() as db:
        referral_id = db.query(Referral).one().id
    client.post(f"/referrals/{referral_id}/status", data={"status": "booked"})
    client.get("/")

    formatter = JsonFormatter()
    lines = [formatter.format(record) for record in caplog.records]
    assert lines, "expected some log output"
    for line in lines:
        json.loads(line)  # every line is valid JSON
        assert "SYN-9999" not in line
        assert "Secret Practice Name" not in line
    assert any('"event": "referral_created"' in line for line in lines)
