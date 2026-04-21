from __future__ import annotations

from openai import OpenAI

from app.config import get_settings


class OpenAIClientFactory:
    @staticmethod
    def create() -> OpenAI:
        settings = get_settings()
        if not settings.openai_api_key:
            raise ValueError('OPENAI_API_KEY is not configured.')
        return OpenAI(api_key=settings.openai_api_key)
