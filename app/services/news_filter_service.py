from __future__ import annotations

from app.models.article import Article, Category


class NewsFilterService:
    def filter_articles(self, articles: list[Article], preferred_categories: list[Category]) -> list[Article]:
        if not preferred_categories:
            return articles
        allowed = {category.name.strip().lower() for category in preferred_categories}
        return [article for article in articles if article.category_name.strip().lower() in allowed]
