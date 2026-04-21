from __future__ import annotations


def truncate(text: str, max_length: int = 280) -> str:
    text = text.strip()
    if len(text) <= max_length:
        return text
    return text[: max_length - 3].rstrip() + '...'
