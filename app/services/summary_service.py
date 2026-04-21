from __future__ import annotations

from app.config import Settings
from app.models.article import Article


class SummaryService:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    def summarize_articles(self, articles: list[Article], language: str = 'az') -> list[Article]:
        # TODO: Replace with OpenAI summarization logic.
        summarized: list[Article] = []
        for article in articles:
            article.summary = article.summary or f'Auto summary placeholder for {article.title}'
            summarized.append(article)
        return summarized
