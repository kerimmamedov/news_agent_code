from __future__ import annotations

import os
import re
from typing import Any

from openai import OpenAI


LANGUAGE_MAP = {
    "az": "Azerbaijani",
    "en": "English",
    "tr": "Turkish",
    "ru": "Russian",
    "fa": "Persian",
    "ua": "Ukrainian",
}


class TranslateService:
    def __init__(self) -> None:
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise ValueError("OPENAI_API_KEY is missing in environment.")

        self.client = OpenAI(api_key=api_key)
        self.model = os.getenv("OPENAI_MODEL_NAME", "gpt-4.1-mini")

    def translate_batch(
        self,
        batch: list[dict[str, Any]],
        target_lang: str,
    ) -> dict[str, dict[str, str]]:
        if not batch:
            return {}

        lang_name = self._normalize_target_lang(target_lang)

        prompt = f"""
Translate each article into {lang_name}.

Rules:
- Output ONLY in the format below (no markdown, no extra text).
- Keep company names, product names, numbers, currencies, percentages, abbreviations, and proper nouns as-is.
- Keep hashtags as hashtags.
- Preserve full length of Summary and Insight.
- Keep EXACTLY TWO prediction sentences at the end of Insight.
- Copy the Link exactly as given.

FORMAT:
===ARTICLE===
Link: <copy exactly>
Title: ...
Summary: ...
Insight: ...
Keywords: ...
===END===
""".strip()

        for rec in batch:
            prompt += f"""

===ARTICLE===
Link: {rec.get("link", "")}
Title: {rec.get("title", "")}
Summary: {rec.get("summary", "")}
Insight: {rec.get("insight", "")}
Keywords: {rec.get("keywords", "")}
===END===
"""

        response = self.client.chat.completions.create(
            model=self.model,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.2,
            max_tokens=3500,
        )

        content = (response.choices[0].message.content or "").strip()
        return self._parse_batch_response(content, target_lang)

    def translate_record(self, rec_en: dict[str, Any], target_lang: str) -> dict[str, str]:
        link = rec_en.get("link") or rec_en.get("news_url") or "__single__"
        batch_input = [
            {
                "link": link,
                "title": rec_en.get("title", ""),
                "summary": rec_en.get("summary", ""),
                "insight": rec_en.get("insight", ""),
                "keywords": rec_en.get("keywords", ""),
            }
        ]
        results = self.translate_batch(batch_input, target_lang)
        translated = results.get(link, {})
        return {
            "title": translated.get("title", "") or rec_en.get("title", ""),
            "summary": translated.get("summary", "") or rec_en.get("summary", ""),
            "insight": translated.get("insight", "") or rec_en.get("insight", ""),
            "keywords": translated.get("keywords", "") or rec_en.get("keywords", ""),
        }

    def _normalize_target_lang(self, target_lang: str) -> str:
        if not target_lang:
            return "English"
        return LANGUAGE_MAP.get(target_lang.lower(), target_lang)

    def _parse_batch_response(
        self,
        content: str,
        target_lang: str,
    ) -> dict[str, dict[str, str]]:
        out: dict[str, dict[str, str]] = {}
        blocks = [block.strip() for block in content.split("===END===") if block.strip()]

        for block in blocks:
            block = re.sub(r"^===ARTICLE===\s*", "", block).strip()
            lines = [line.strip() for line in block.splitlines() if line.strip()]

            link = ""
            title = ""
            summary = ""
            insight = ""
            keywords = ""

            for line in lines:
                lowered = line.lower()
                if lowered.startswith("link:"):
                    link = line.split(":", 1)[1].strip()
                elif lowered.startswith("title:"):
                    title = line.split(":", 1)[1].strip()
                elif lowered.startswith("summary:"):
                    summary = line.split(":", 1)[1].strip()
                elif lowered.startswith("insight:"):
                    insight = line.split(":", 1)[1].strip()
                elif lowered.startswith("keywords:"):
                    raw_keywords = line.split(":", 1)[1].strip()
                    parts = [
                        part.strip().lstrip("#").rstrip(",")
                        for part in re.split(r"\s+", raw_keywords)
                        if part.strip()
                    ]
                    keywords = "".join(parts)

            if not link:
                continue

            out[link] = {
                "language": target_lang,
                "link": link,
                "title": title,
                "summary": summary,
                "insight": insight,
                "keywords": keywords,
            }

        return out
