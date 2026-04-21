from __future__ import annotations

from collections import OrderedDict
from difflib import SequenceMatcher
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from app.db.repositories import (
    get_recent_news_by_category,
    get_sent_article_links_for_email,
    get_user_categories_map,
    get_users_with_email,
)


LANG_CODE_MAP = {
    "AZ": "az",
    "EN": "en",
    "TR": "tr",
    "RU": "ru",
    "UA": "ua",
    "FA": "fa",
    "az": "az",
    "en": "en",
    "tr": "tr",
    "ru": "ru",
    "ua": "ua",
    "fa": "fa",
}

SIMILARITY_THRESHOLD = 0.8
TRACKING_PARAMS = {
    "utm_source",
    "utm_medium",
    "utm_campaign",
    "utm_term",
    "utm_content",
    "fbclid",
    "gclid",
    "mc_cid",
    "mc_eid",
    "ref",
    "rss",
}


def _normalize_lang_code(lang: str | None) -> str:
    if not lang:
        return ""
    return LANG_CODE_MAP.get(str(lang).strip(), str(lang).strip().lower())


def _normalize_link(url: str) -> str:
    if not url:
        return ""

    parts = urlsplit(url.strip())
    scheme = parts.scheme.lower()
    netloc = parts.netloc.lower().replace("www.", "")
    path = parts.path.rstrip("/")
    query_pairs = [
        (key, value)
        for key, value in parse_qsl(parts.query, keep_blank_values=True)
        if key.lower() not in TRACKING_PARAMS
    ]
    query = urlencode(sorted(query_pairs))
    return urlunsplit((scheme, netloc, path, query, ""))


def _is_similar(a: str, b: str, threshold: float = SIMILARITY_THRESHOLD) -> bool:
    a = (a or "").strip().lower()
    b = (b or "").strip().lower()
    if not a or not b:
        return False
    return SequenceMatcher(None, a, b).ratio() >= threshold


def _remove_duplicates(articles: list[dict]) -> list[dict]:
    unique_rows: list[dict] = []

    for article in articles:
        current_title = article.get("title", "")
        current_summary = article.get("summary", "")
        current_norm_link = article.get("link_norm", "")

        is_duplicate = False
        for kept in unique_rows:
            kept_title = kept.get("title", "")
            kept_summary = kept.get("summary", "")
            kept_norm_link = kept.get("link_norm", "")

            if current_norm_link and kept_norm_link and current_norm_link == kept_norm_link:
                is_duplicate = True
                break
            if _is_similar(current_title, kept_title):
                is_duplicate = True
                break
            if _is_similar(current_summary, kept_summary):
                is_duplicate = True
                break

        if not is_duplicate:
            unique_rows.append(article)

    return unique_rows


def _normalize_articles(articles: list[dict]) -> list[dict]:
    normalized = []
    for article in articles:
        normalized.append(
            {
                "id": article.get("id"),
                "title": article.get("title") or "Untitled",
                "summary": article.get("summary") or "",
                "insight": article.get("insight") or "",
                "keywords": article.get("keywords") or "",
                "news_url": article.get("news_url") or "",
                "image_url": article.get("image_url"),
                "news_date": article.get("news_date"),
                "news_lang": article.get("news_lang"),
                "category_id": article.get("category_id"),
                "category_name": article.get("category_name") or "General",
                "link_norm": _normalize_link(article.get("news_url") or ""),
            }
        )
    return normalized


def _sort_articles_notebook_style(articles: list[dict]) -> list[dict]:
    return sorted(
        articles,
        key=lambda article: (
            article.get("category_name") or "",
            article.get("title") or "",
        ),
    )


def _select_articles_for_user(
    articles: list[dict],
    user_categories: list[str],
    total: int,
) -> list[dict]:
    if not articles:
        return []

    if total <= 0:
        return []

    if not user_categories:
        return articles[:total]

    selected: list[dict] = []
    used_links: set[str] = set()

    base = total // len(user_categories)
    remainder = total % len(user_categories)

    for index, category_name in enumerate(user_categories):
        quota = base + (1 if index < remainder else 0)
        category_key = str(category_name or "").lower()

        taken_for_category = 0
        for article in articles:
            link_norm = article.get("link_norm", "")
            if not link_norm or link_norm in used_links:
                continue
            if str(article.get("category_name", "")).lower() != category_key:
                continue

            selected.append(article)
            used_links.add(link_norm)
            taken_for_category += 1

            if len(selected) >= total or taken_for_category >= quota:
                break

        if len(selected) >= total:
            break

    if len(selected) < total:
        for article in articles:
            link_norm = article.get("link_norm", "")
            if not link_norm or link_norm in used_links:
                continue

            selected.append(article)
            used_links.add(link_norm)

            if len(selected) >= total:
                break

    return selected


def _build_subject(user_lang: str, category_names: list[str]) -> str:
    return "Your Daily News"


def build_user_digest(
    user: dict,
    user_categories: list[dict],
    max_articles: int | None = None,
) -> dict | None:
    user_id = user["id"]
    user_email = user["email"]
    username = user.get("username") or "User"
    user_lang = user.get("user_lang") or "en"
    db_lang = (_normalize_lang_code(user_lang) or "en").upper()

    if not user_categories:
        return None

    sent_links = get_sent_article_links_for_email(user_email)
    sent_links_norm = {_normalize_link(link) for link in sent_links if link}

    all_articles = []
    for category in user_categories:
        category_id = category["category_id"]
        category_articles = get_recent_news_by_category(
            user_id=user_id,
            category_id=category_id,
            news_lang=db_lang,
        )
        all_articles.extend(category_articles)

    all_articles = _normalize_articles(all_articles)

    filtered = []
    for article in all_articles:
        link_norm = article.get("link_norm", "")
        if not link_norm:
            continue
        if link_norm in sent_links_norm:
            continue
        filtered.append(article)

    if not filtered:
        return None

    deduped_exact = OrderedDict()
    for article in filtered:
        key = article["link_norm"]
        if key not in deduped_exact:
            deduped_exact[key] = article

    articles = list(deduped_exact.values())
    articles = _remove_duplicates(articles)
    articles = _sort_articles_notebook_style(articles)

    if not articles:
        return None

    category_names = [category["category_name"] for category in user_categories]
    article_limit = max_articles if max_articles is not None else 50
    articles = _select_articles_for_user(articles, category_names, total=article_limit)

    if not articles:
        return None

    subject = _build_subject(user_lang=user_lang, category_names=sorted(set(category_names)))

    return {
        "user": user,
        "username": username,
        "email": user_email,
        "categories": sorted(set(category_names)),
        "articles": articles,
        "subject": subject,
        "article_count": len(articles),
    }


def build_all_user_digests(max_articles: int | None = None) -> list[dict]:
    users = get_users_with_email()
    category_map = get_user_categories_map()
    digests = []

    for user in users:
        user_categories = category_map.get(user["id"], [])
        digest = build_user_digest(
            user=user,
            user_categories=user_categories,
            max_articles=max_articles,
        )
        if digest:
            digests.append(digest)

    return digests
