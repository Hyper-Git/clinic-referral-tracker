"""Reads every setting from environment variables. Nothing else in the app hard-codes config."""
import os


def _required(name: str) -> str:
    value = os.environ.get(name)
    if not value:
        raise RuntimeError(f"Required environment variable {name} is not set")
    return value


def _int(name: str, default: int) -> int:
    raw = os.environ.get(name)
    if raw is None or raw == "":
        return default
    try:
        return int(raw)
    except ValueError as exc:
        raise RuntimeError(f"Environment variable {name} must be a whole number, got {raw!r}") from exc


class Settings:
    def __init__(self) -> None:
        self.database_url = _required("DATABASE_URL")
        self.app_host = os.environ.get("APP_HOST", "0.0.0.0")
        self.app_port = _int("APP_PORT", 8000)
        self.urgent_threshold_days = _int("URGENT_THRESHOLD_DAYS", 14)
        self.routine_threshold_days = _int("ROUTINE_THRESHOLD_DAYS", 42)
        self.db_connect_timeout = _int("DB_CONNECT_TIMEOUT", 3)
        self.log_level = os.environ.get("LOG_LEVEL", "INFO").upper()


settings = Settings()
