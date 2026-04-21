from __future__ import annotations

import psycopg2
from psycopg2.extensions import connection as PgConnection

from app.config import get_settings



def get_connection() -> PgConnection:
    settings = get_settings()
    return psycopg2.connect(
        host=settings.db_host,
        port=settings.db_port,
        dbname=settings.db_name,
        user=settings.db_user,
        password=settings.db_password,
        sslmode=settings.db_sslmode,
        connect_timeout=15,
        keepalives=1,
        keepalives_idle=30,
        keepalives_interval=10,
        keepalives_count=5,
        options='-c statement_timeout=10000 -c timezone=Asia/Baku',
    )
