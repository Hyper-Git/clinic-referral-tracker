"""Test setup. Tests use a throwaway SQLite file, so no PostgreSQL is needed to run them."""
import os
import tempfile

# Must be set before the app modules are imported (config is read at import time).
_tmpdir = tempfile.mkdtemp()
os.environ["DATABASE_URL"] = f"sqlite:///{_tmpdir}/test.db"
os.environ["URGENT_THRESHOLD_DAYS"] = "14"
os.environ["ROUTINE_THRESHOLD_DAYS"] = "42"

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

import database  # noqa: E402
from main import app  # noqa: E402


@pytest.fixture
def client():
    database.create_tables()
    with TestClient(app) as c:
        yield c
    database.Base.metadata.drop_all(database.engine)
