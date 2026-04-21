from __future__ import annotations

import os
import re

from openai import OpenAI


class SummarizerService:
    def __init__(self) -> None:
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise ValueError("OPENAI_API_KEY is missing in environment.")

        self.client = OpenAI(api_key=api_key)
        self.model = os.getenv("OPENAI_MODEL_NAME", "gpt-4.1-mini")

    def analyze_batch(
        self,
        batch: list[dict],
        allowed_categories: list[str],
    ) -> dict[str, dict[str, str]]:
        if not batch:
            return {}

        allowed_text = ", ".join(allowed_categories)
        prompt = f"""
You are a financial news assistant.

Allowed categories (choose ONLY one): {allowed_text}
If the article does NOT clearly fit any category, you MUST output: Category: OTHER

Hard rules:
- NEVER invent a new category.
- NEVER force-fit into a category. If unsure, use OTHER.
- Output must be in ENGLISH.
- Summary: at least 7 sentences.
- Insight: at least 7 sentences.
- After Insight, add a FINAL paragraph with exactly TWO predictions (2 sentences total, one prediction per sentence).
- Keywords: 3-5 hashtags.
- Preserve company names, product names, numbers, currencies, percentages, abbreviations, and proper nouns.
- Do not hallucinate facts not supported by the source.

Return results for each article in EXACTLY this format:

===ARTICLE===
Title: <clean English title>
Category: <one of allowed categories OR OTHER>
Summary: <min 7 sentences>
Insight: <min 7 sentences>
Predictions: <exactly 2 sentences, each a prediction>
Keywords: <3-5 hashtags>
Link: <copy the link>
===END===

Now process these articles:
""".strip()

        for index, row in enumerate(batch, 1):
            title = (row.get("title") or "").strip()
            summary = (row.get("summary") or "").strip()
            link = (row.get("link") or row.get("news_url") or "").strip()
            prompt += f"\n[{index}] Title: {title}\nSnippet: {summary}\nLink: {link}\n"

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.4,
                max_tokens=2500,
            )
            content = (response.choices[0].message.content or "").strip()
        except Exception:
            content = self._build_fallback_content(batch)

        blocks = [block.strip() for block in content.split("===END===") if block.strip()]
        result: dict[str, dict[str, str]] = {}

        for block in blocks:
            parsed = self._parse_block(block)
            link = parsed.get("link", "").strip()
            if not link:
                continue
            result[link] = parsed

        return result

    def summarize_news(
        self,
        *,
        title: str,
        summary: str,
        source_url: str,
        allowed_categories: list[str],
    ) -> dict[str, str]:
        batch = [
            {
                "title": title,
                "summary": summary,
                "link": source_url,
            }
        ]
        results = self.analyze_batch(batch=batch, allowed_categories=allowed_categories)
        parsed = results.get(source_url, {})
        return {
            "title": parsed.get("title", title),
            "category_name": parsed.get("category_name", "OTHER"),
            "summary": parsed.get("summary", summary),
            "insight": parsed.get("insight", ""),
            "keywords": parsed.get("keywords", ""),
            "link": source_url,
        }

    def _parse_block(self, block: str) -> dict[str, str]:
        block = re.sub(r"^===ARTICLE===\s*", "", block).strip()
        lines = [line.strip() for line in block.splitlines() if line.strip()]

        parsed = {
            "title": "",
            "category_name": "OTHER",
            "summary": "",
            "insight": "",
            "keywords": "",
            "link": "",
        }
        predictions = ""

        for line in lines:
            lowered = line.lower()
            if lowered.startswith("title:"):
                parsed["title"] = line.split(":", 1)[1].strip()
            elif lowered.startswith("category:"):
                category_value = line.split(":", 1)[1].strip()
                parsed["category_name"] = category_value or "OTHER"
            elif lowered.startswith("summary:"):
                parsed["summary"] = line.split(":", 1)[1].strip()
            elif lowered.startswith("insight:"):
                parsed["insight"] = line.split(":", 1)[1].strip()
            elif lowered.startswith("predictions:"):
                predictions = line.split(":", 1)[1].strip()
            elif lowered.startswith("keywords:"):
                raw_keywords = line.split(":", 1)[1].strip()
                parts = [
                    part.strip().lstrip("#").rstrip(",")
                    for part in re.split(r"\s+", raw_keywords)
                    if part.strip()
                ]
                parsed["keywords"] = "".join(parts)
            elif lowered.startswith("link:"):
                parsed["link"] = line.split(":", 1)[1].strip()

        if predictions:
            combined = " ".join(part for part in [parsed["insight"], predictions] if part)
            parsed["insight"] = combined.strip()

        return parsed

    def _build_fallback_content(self, batch: list[dict]) -> str:
        blocks = []
        for row in batch:
            title = (row.get("title") or "").strip()
            summary = (row.get("summary") or "").strip()
            link = (row.get("link") or row.get("news_url") or "").strip()
            blocks.append(
                "\n".join(
                    [
                        "===ARTICLE===",
                        f"Title: {title}",
                        "Category: OTHER",
                        f"Summary: {summary}",
                        "Insight: ",
                        "Predictions: ",
                        "Keywords: ",
                        f"Link: {link}",
                        "===END===",
                    ]
                )
            )
        return "\n".join(blocks)
