"""Database connection: one SQLAlchemy engine shared by the whole app."""
from sqlalchemy import create_engine, text
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from config import settings


class Base(DeclarativeBase):
    pass


def make_engine(url: str, connect_timeout: int):
    connect_args = {}
    if url.startswith("postgresql"):
        # Fail fast if the database is unreachable, so /health answers quickly.
        connect_args["connect_timeout"] = connect_timeout
    elif url.startswith("sqlite"):
        # Only used by the tests; lets FastAPI's worker threads share the file.
        connect_args["check_same_thread"] = False
    return create_engine(
        url,
        connect_args=connect_args,
        pool_pre_ping=True,     # check a pooled connection still works before using it
        hide_parameters=True,   # keep data values out of error messages and logs
    )


engine = make_engine(settings.database_url, settings.db_connect_timeout)
SessionLocal = sessionmaker(bind=engine, expire_on_commit=False)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def database_is_reachable() -> bool:
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return True
    except Exception:
        return False


def create_tables() -> None:
    import models  # noqa: F401  (registers the tables on Base)
    Base.metadata.create_all(engine)
