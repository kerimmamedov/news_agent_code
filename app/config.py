from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

# Load .env from project root if present
PROJECT_ROOT = Path(__file__).resolve().parents[1]
load_dotenv(PROJECT_ROOT / '.env')


def _get_env(name: str, default: str | None = None, required: bool = False) -> str:
    value = os.getenv(name, default)
    if required and (value is None or str(value).strip() == ''):
        raise ValueError(f'Missing required environment variable: {name}')
    return '' if value is None else value


def _get_int(name: str, default: int) -> int:
    raw = os.getenv(name)
    if raw is None or raw.strip() == '':
        return default
    try:
        return int(raw)
    except ValueError as exc:
        raise ValueError(f'Environment variable {name} must be an integer, got: {raw}') from exc


@dataclass(frozen=True)
class Settings:
    db_host: str
    db_port: int
    db_name: str
    db_user: str
    db_password: str
    db_sslmode: str

    openai_api_key: str
    openai_model_name: str

    email_sender: str
    email_password: str
    email_host: str
    email_port: int
    email_use_tls: bool

    app_timezone: str
    log_level: str
    batch_size: int



def get_settings() -> Settings:
    return Settings(
        db_host=_get_env('DB_HOST', required=True),
        db_port=_get_int('DB_PORT', 5432),
        db_name=_get_env('DB_NAME', required=True),
        db_user=_get_env('DB_USER', required=True),
        db_password=_get_env('DB_PASSWORD', required=True),
        db_sslmode=_get_env('DB_SSLMODE', 'prefer'),
        openai_api_key=_get_env('OPENAI_API_KEY', ''),
        openai_model_name=_get_env('OPENAI_MODEL_NAME', 'gpt-4.1-mini'),
        email_sender=_get_env('EMAIL_SENDER', ''),
        email_password=_get_env('EMAIL_PASSWORD', ''),
        email_host=_get_env('EMAIL_HOST', 'smtp.gmail.com'),
        email_port=_get_int('EMAIL_PORT', 587),
        email_use_tls=_get_env('EMAIL_USE_TLS', 'true').lower() in {'1', 'true', 'yes', 'y'},
        app_timezone=_get_env('APP_TIMEZONE', 'Asia/Baku'),
        log_level=_get_env('LOG_LEVEL', 'INFO'),
        batch_size=_get_int('BATCH_SIZE', 100),
    )
