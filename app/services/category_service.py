from __future__ import annotations

from app.models.article import Category


class CategoryService:
    def normalize(self, categories: list[Category]) -> list[Category]:
        unique: dict[str, Category] = {}
        for category in categories:
            unique[category.name.strip().lower()] = category
        return list(unique.values())
