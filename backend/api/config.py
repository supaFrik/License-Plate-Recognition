import os
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

from dotenv import load_dotenv


load_dotenv(Path(__file__).resolve().parents[1] / ".env")


def _parse_bool(value: str | None, default: bool) -> bool:
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _parse_csv(value: str | None, default: list[str]) -> list[str]:
    if not value:
        return default
    return [item.strip() for item in value.split(",") if item.strip()]


@dataclass(frozen=True)
class Settings:
    app_name: str
    app_description: str
    database_url: str
    cors_origins: list[str]
    access_token_minutes: int
    refresh_token_days: int
    jwt_secret_key: str
    jwt_algorithm: str
    refresh_cookie_name: str
    refresh_cookie_secure: bool
    refresh_cookie_samesite: str
    refresh_cookie_domain: str | None
    bootstrap_admin_email: str | None
    bootstrap_admin_password: str | None
    auth_rate_limit_window_seconds: int
    auth_rate_limit_max_requests: int
    warm_model_on_startup: bool


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    default_database_url = (
        "mysql+pymysql://root:trinhquocviet2005@localhost:3306/"
        "license_plate_recognition"
    )
    return Settings(
        app_name="VietPlateAI API",
        app_description=(
            "Operations API for VietPlateAI vehicle detection, access monitoring, "
            "and audit history."
        ),
        database_url=os.getenv("DATABASE_URL", default_database_url),
        cors_origins=_parse_csv(
            os.getenv("CORS_ORIGINS"),
            ["http://127.0.0.1:8080", "http://localhost:8080"],
        ),
        access_token_minutes=int(os.getenv("ACCESS_TOKEN_MINUTES", "15")),
        refresh_token_days=int(os.getenv("REFRESH_TOKEN_DAYS", "7")),
        jwt_secret_key=os.getenv(
            "JWT_SECRET_KEY",
            "vietplateai-local-dev-secret-change-me",
        ),
        jwt_algorithm=os.getenv("JWT_ALGORITHM", "HS256"),
        refresh_cookie_name=os.getenv(
            "REFRESH_COOKIE_NAME",
            "vietplate_refresh_token",
        ),
        refresh_cookie_secure=_parse_bool(
            os.getenv("REFRESH_COOKIE_SECURE"),
            False,
        ),
        refresh_cookie_samesite=os.getenv("REFRESH_COOKIE_SAMESITE", "lax"),
        refresh_cookie_domain=os.getenv("REFRESH_COOKIE_DOMAIN") or None,
        bootstrap_admin_email=os.getenv("BOOTSTRAP_ADMIN_EMAIL") or None,
        bootstrap_admin_password=os.getenv("BOOTSTRAP_ADMIN_PASSWORD") or None,
        auth_rate_limit_window_seconds=int(
            os.getenv("AUTH_RATE_LIMIT_WINDOW_SECONDS", "60")
        ),
        auth_rate_limit_max_requests=int(
            os.getenv("AUTH_RATE_LIMIT_MAX_REQUESTS", "10")
        ),
        warm_model_on_startup=_parse_bool(
            os.getenv("WARM_MODEL_ON_STARTUP"),
            True,
        ),
    )
