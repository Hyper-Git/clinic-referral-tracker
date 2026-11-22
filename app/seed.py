"""Inserts 15 synthetic referrals. Safe to run more than once: existing references are skipped.

Run from the app/ folder:  python seed.py
"""
import logging
from datetime import date, timedelta

from sqlalchemy import select

import database
from config import settings
from logging_config import setup_logging
from models import Referral

# (reference, practice, priority, status, days_ago). All values are made up.
SEED_DATA = [
    ("SYN-1001", "Riverside Medical Centre", "urgent", "received", 3),
    ("SYN-1002", "Oakfield Surgery", "routine", "received", 10),
    ("SYN-1003", "Hillview Health Practice", "urgent", "triaged", 18),
    ("SYN-1004", "Meadowbank GP Group", "routine", "booked", 50),
    ("SYN-1005", "Riverside Medical Centre", "routine", "triaged", 30),
    ("SYN-1006", "Northgate Family Practice", "urgent", "booked", 7),
    ("SYN-1007", "Oakfield Surgery", "routine", "seen", 60),
    ("SYN-1008", "Elm Street Surgery", "urgent", "received", 21),
    ("SYN-1009", "Hillview Health Practice", "routine", "received", 44),
    ("SYN-1010", "Meadowbank GP Group", "urgent", "seen", 12),
    ("SYN-1011", "Northgate Family Practice", "routine", "triaged", 15),
    ("SYN-1012", "Elm Street Surgery", "routine", "received", 2),
    ("SYN-1013", "Riverside Medical Centre", "urgent", "triaged", 1),
    ("SYN-1014", "Oakfield Surgery", "routine", "booked", 38),
    ("SYN-1015", "Hillview Health Practice", "urgent", "received", 14),
]


def seed() -> int:
    database.create_tables()
    today = date.today()
    inserted = 0
    with database.SessionLocal() as db:
        existing = set(db.scalars(select(Referral.reference)))
        for reference, practice, priority, status, days_ago in SEED_DATA:
            if reference in existing:
                continue
            db.add(Referral(reference=reference, referring_practice=practice, priority=priority,
                            status=status, date_received=today - timedelta(days=days_ago)))
            inserted += 1
        db.commit()
    return inserted


if __name__ == "__main__":
    setup_logging(settings.log_level)
    count = seed()
    logging.getLogger("seed").info("seed complete", extra={"event": "seed_complete", "count": count})
