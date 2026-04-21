from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True)
class User:
    id: int
    email: str
    language: str = 'az'
