from __future__ import annotations

from collections import defaultdict
from typing import Any
from urllib.parse import urlparse

from app.db import queries
from app.db.connection import get_connection


_CATEGORY_NAME_TO_ID: dict[str, str] = {}
_SITE_DOMAIN_TO_ID: dict[str, str] = {}


def fetch_all(query: str, params: tuple | None = None) -> list[tuple]:
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(query, params or ())
            return cur.fetchall()


def fetch_one(query: str, params: tuple | None = None) -> tuple | None:
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(query, params or ())
            return cur.fetchone()


def execute(query: str, params: tuple | None = None) -> None:
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(query, params or ())
        conn.commit()


def get_all_categories() -> list[dict[str, str]]:
    rows = fetch_all(queries.GET_ALL_CATEGORIES)
    categories: list[dict[str, str]] = []

    for row in rows:
        category_id, category_name = row
        if not category_name:
            continue
        categories.append(
            {
                "category_id": str(category_id),
                "category_name": category_name,
            }
        )

    return categories


def get_users_with_email() -> list[dict[str, Any]]:
    rows = fetch_all(queries.GET_USERS_WITH_EMAIL)
    result = []

    for row in rows:
        result.append(
            {
                "id": str(row[0]),
                "email": row[1],
                "username": row[2],
                "user_lang": row[3],
                "status": row[4],
            }
        )

    return result


def get_user_categories_map() -> dict[str, list[dict[str, str]]]:
    rows = fetch_all(queries.GET_USER_CATEGORIES)
    result: dict[str, list[dict[str, str]]] = defaultdict(list)

    for row in rows:
        user_id, category_id, category_name = row
        result[str(user_id)].append(
            {
                "category_id": str(category_id),
                "category_name": category_name,
            }
        )

    return dict(result)


def get_recent_news_by_category(
    user_id: str,
    category_id: str,
    news_lang: str,
) -> list[dict[str, Any]]:
    rows = fetch_all(
        queries.GET_RECENT_NEWS_BY_CATEGORY,
        (user_id, category_id, news_lang),
    )
    result = []

    for row in rows:
        result.append(
            {
                "id": str(row[0]),
                "title": row[1],
                "summary": row[2],
                "insight": row[3],
                "keywords": row[4],
                "news_url": row[5],
                "image_url": row[6],
                "news_date": row[7],
                "news_lang": row[8],
                "category_id": str(row[9]),
                "category_name": row[10],
            }
        )

    return result


def get_sent_article_links_for_email(email: str) -> set[str]:
    rows = fetch_all(queries.GET_ALREADY_SENT_ARTICLE_LINKS_FOR_EMAIL, (email,))
    return {row[0] for row in rows if row[0]}


def save_sent_article(article_link: str, article_title: str, user_email: str) -> None:
    execute(queries.INSERT_SENT_ARTICLE, (article_link, article_title, user_email))


def get_all_sites() -> list[str]:
    rows = fetch_all(queries.GET_ALL_SITES)
    return [row[0] for row in rows if row[0]]


def _load_category_cache() -> None:
    if _CATEGORY_NAME_TO_ID:
        return

    for category in get_all_categories():
        name = (category["category_name"] or "").strip().lower()
        if not name:
            continue
        _CATEGORY_NAME_TO_ID[name] = category["category_id"]


def _load_site_cache() -> None:
    if _SITE_DOMAIN_TO_ID:
        return

    rows = fetch_all(queries.GET_ALL_SITE_IDS)
    for row in rows:
        site_id, site_url = row
        if not site_url:
            continue

        domain = urlparse(site_url).netloc.lower()
        root_domain = domain[4:] if domain.startswith("www.") else domain
        if domain:
            _SITE_DOMAIN_TO_ID[domain] = str(site_id)
        if root_domain:
            _SITE_DOMAIN_TO_ID[root_domain] = str(site_id)


def resolve_category_id(category_name: str | None) -> str | None:
    if not category_name:
        return None

    _load_category_cache()

    key = category_name.strip().lower()
    if not key:
        return None

    direct = _CATEGORY_NAME_TO_ID.get(key)
    if direct is not None:
        return direct

    tokens = {token for token in key.replace("&", " ").replace("/", " ").split() if token}
    best_id: str | None = None
    best_score = 0.0

    if tokens:
        for candidate_name, candidate_id in _CATEGORY_NAME_TO_ID.items():
            candidate_tokens = {
                token
                for token in candidate_name.replace("&", " ").replace("/", " ").split()
                if token
            }
            overlap = len(tokens & candidate_tokens)
            if overlap == 0 or not candidate_tokens:
                continue
            score = overlap / len(candidate_tokens)
            if score > best_score:
                best_score = score
                best_id = candidate_id

    if best_id is not None:
        return best_id

    row = fetch_one(queries.FIND_CATEGORY_ID_BY_LIKE, (f"%{category_name}%",))
    if row:
        category_id = str(row[0])
        _CATEGORY_NAME_TO_ID[key] = category_id
        return category_id

    return None


def get_or_create_site_id_from_link(link: str | None) -> str | None:
    if not link:
        return None

    _load_site_cache()

    domain = urlparse(link).netloc.lower()
    root_domain = domain[4:] if domain.startswith("www.") else domain

    for value in (domain, root_domain):
        if value and value in _SITE_DOMAIN_TO_ID:
            return _SITE_DOMAIN_TO_ID[value]

    if not root_domain:
        return None

    site_url = f"https://{root_domain}/"

    existing = fetch_one(queries.GET_SITE_ID_BY_URL, (site_url,))
    if existing:
        site_id = str(existing[0])
        _SITE_DOMAIN_TO_ID[domain] = site_id
        _SITE_DOMAIN_TO_ID[root_domain] = site_id
        return site_id

    try:
        created = fetch_one(queries.INSERT_SITE, (site_url,))
    except Exception:
        created = fetch_one(queries.GET_SITE_ID_BY_URL, (site_url,))

    if not created:
        return None

    site_id = str(created[0])
    _SITE_DOMAIN_TO_ID[domain] = site_id
    _SITE_DOMAIN_TO_ID[root_domain] = site_id
    return site_id


def save_news_item_for_user(
    *,
    image_url: str | None,
    insight: str,
    keywords: str,
    news_date,
    news_lang: str,
    news_url: str,
    summary: str,
    title: str,
    category_id: str | None,
    user_id: str,
) -> None:
    if not news_url or not title or not summary:
        return

    site_id = get_or_create_site_id_from_link(news_url)

    execute(
        queries.INSERT_NEWS_ITEM_FOR_USER,
        (
            image_url,
            insight,
            keywords,
            news_date,
            str(news_lang or "").upper(),
            news_url,
            site_id,
            summary,
            title,
            category_id,
            user_id,
        ),
    )
