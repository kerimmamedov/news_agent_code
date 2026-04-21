from __future__ import annotations

import time
from collections.abc import Callable
from typing import TypeVar

T = TypeVar('T')



def retry(fn: Callable[[], T], retries: int = 2, sleep_seconds: float = 1.0) -> T:
    last_error: Exception | None = None
    for attempt in range(retries + 1):
        try:
            return fn()
        except Exception as exc:  # noqa: BLE001
            last_error = exc
            if attempt == retries:
                break
            time.sleep(sleep_seconds * (attempt + 1))
    assert last_error is not None
    raise last_error
