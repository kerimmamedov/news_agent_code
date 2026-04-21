from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True)
class NewsletterContent:
    subject: str
    html_body: str
    text_body: str
