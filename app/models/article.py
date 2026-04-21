from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True)
class Category:
    id: int
    name: str


@dataclass(slots=True)
class Article:
    title: str
    url: str
    source: str
    summary: str = ''
    category_name: str = ''
