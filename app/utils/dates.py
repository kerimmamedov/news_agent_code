from __future__ import annotations

from datetime import datetime
from zoneinfo import ZoneInfo



def now_in_timezone(tz_name: str) -> datetime:
    return datetime.now(ZoneInfo(tz_name))
