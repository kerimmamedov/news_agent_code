from __future__ import annotations

from collections import defaultdict
from datetime import datetime
from difflib import SequenceMatcher
import os
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from dotenv import load_dotenv

from app.db.repositories import (
    get_all_categories,
    get_all_sites,
    get_user_categories_map,
    get_users_with_email,
    save_news_item_for_user,
)
from app.services.news_fetch_service import NewsFetchService
from app.services.summarizer_service import SummarizerService
from app.services.translate_service import TranslateService


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


def log(message: str) -> None:
    print(message, flush=True)


def normalize_site_url(url: str) -> str:
    return (url or "").strip().rstrip("/")


def normalize_link(url: str) -> str:
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


def is_similar(a: str, b: str, threshold: float = SIMILARITY_THRESHOLD) -> bool:
    a_text = (a or "").strip().lower()
    b_text = (b or "").strip().lower()
    if not a_text or not b_text:
        return False
    return SequenceMatcher(None, a_text, b_text).ratio() >= threshold


def remove_duplicates(records: list[dict]) -> list[dict]:
    unique_rows: list[dict] = []

    for row in records:
        current_title = row.get("title", "")
        current_summary = row.get("summary", "")
        current_link = row.get("link_norm", "")

        duplicate = False
        for kept in unique_rows:
            if current_link and current_link == kept.get("link_norm", ""):
                duplicate = True
                break
            if is_similar(current_title, kept.get("title", "")):
                duplicate = True
                break
            if is_similar(current_summary, kept.get("summary", "")):
                duplicate = True
                break

        if not duplicate:
            unique_rows.append(row)

    return unique_rows


def parse_news_date(published_value: str):
    if not published_value:
        return datetime.now().date()

    try:
        return datetime.fromisoformat(published_value.replace("Z", "+00:00")).date()
    except Exception:
        return datetime.now().date()


def build_language_variants_batch(
    records: list[dict],
    allowed_categories: list[str],
    summarizer: SummarizerService,
    translator: TranslateService,
    batch_size: int,
) -> dict[str, dict[str, dict]]:
    if not records:
        return {}

    en_results: dict[str, dict] = {}
    for index in range(0, len(records), batch_size):
        batch = records[index:index + batch_size]
        total_batches = (len(records) + batch_size - 1) // batch_size
        log(f"EN analyze batch {index // batch_size + 1}/{total_batches}")
        batch_results = summarizer.analyze_batch(batch=batch, allowed_categories=allowed_categories)
        en_results.update(batch_results)

    translation_input: list[dict] = []
    for record in records:
        link = record.get("link", "")
        en_payload = en_results.get(link, {})
        category_name = en_payload.get("category_name", "OTHER")
        if not en_payload or category_name == "OTHER":
            continue

        translation_input.append(
            {
                "link": link,
                "title": en_payload.get("title") or record.get("title", ""),
                "summary": en_payload.get("summary") or record.get("summary", ""),
                "insight": en_payload.get("insight", ""),
                "keywords": en_payload.get("keywords", ""),
            }
        )

    az_results: dict[str, dict] = {}
    fa_results: dict[str, dict] = {}

    for index in range(0, len(translation_input), batch_size):
        batch = translation_input[index:index + batch_size]
        if not batch:
            continue

        total_translation_batches = (len(translation_input) + batch_size - 1) // batch_size

        try:
            log(f"AZ translate batch {index // batch_size + 1}/{total_translation_batches}")
            az_results.update(translator.translate_batch(batch, "az"))
        except Exception as exc:
            log(f"Batch translation failed for AZ batch {index // batch_size}: {exc}")

        try:
            log(f"FA translate batch {index // batch_size + 1}/{total_translation_batches}")
            fa_results.update(translator.translate_batch(batch, "fa"))
        except Exception as exc:
            log(f"Batch translation failed for FA batch {index // batch_size}: {exc}")

    out: dict[str, dict[str, dict]] = {}
    for record in records:
        link = record.get("link", "")
        link_norm = normalize_link(link)
        en_payload = en_results.get(link, {})
        if not en_payload:
            continue

        category_name = en_payload.get("category_name", "OTHER")
        if category_name == "OTHER":
            continue

        base = {
            "link": link,
            "category_name": category_name,
            "image_url": record.get("image_url"),
        }

        out[link_norm] = {
            "EN": {
                **base,
                "title": en_payload.get("title") or record.get("title", ""),
                "summary": en_payload.get("summary") or record.get("summary", ""),
                "insight": en_payload.get("insight", ""),
                "keywords": en_payload.get("keywords", ""),
            },
            "AZ": {
                **base,
                "title": az_results.get(link, {}).get("title") or en_payload.get("title") or record.get("title", ""),
                "summary": az_results.get(link, {}).get("summary") or en_payload.get("summary") or record.get("summary", ""),
                "insight": az_results.get(link, {}).get("insight") or en_payload.get("insight", ""),
                "keywords": az_results.get(link, {}).get("keywords") or en_payload.get("keywords", ""),
            },
            "FA": {
                **base,
                "title": fa_results.get(link, {}).get("title") or en_payload.get("title") or record.get("title", ""),
                "summary": fa_results.get(link, {}).get("summary") or en_payload.get("summary") or record.get("summary", ""),
                "insight": fa_results.get(link, {}).get("insight") or en_payload.get("insight", ""),
                "keywords": fa_results.get(link, {}).get("keywords") or en_payload.get("keywords", ""),
            },
        }

    return out


def main():
    load_dotenv()

    batch_size = int(os.getenv("BATCH_SIZE", "5"))
    limit_per_site = int(os.getenv("FETCH_LIMIT_PER_SITE", "5") or "5")
    max_sites = int(os.getenv("MAX_SITES", "0") or "0")

    users = get_users_with_email()
    all_categories = get_all_categories()
    user_categories_map = get_user_categories_map()
    raw_site_urls = get_all_sites()

    if not users:
        log("No active users with email found.")
        return

    if not all_categories:
        log("No categories found in database.")
        return

    seen_sites = set()
    site_urls = []
    for url in raw_site_urls:
        normalized = normalize_site_url(url)
        if normalized and normalized not in seen_sites:
            seen_sites.add(normalized)
            site_urls.append(normalized)

    if max_sites > 0:
        site_urls = site_urls[:max_sites]

    if not site_urls:
        log("No sites found in sites table.")
        return

    users_by_id = {user["id"]: user for user in users}
    category_name_to_id = {
        category["category_name"]: category["category_id"]
        for category in all_categories
    }
    allowed_categories = [category["category_name"] for category in all_categories]
    category_to_users: dict[str, list[dict]] = defaultdict(list)

    for user_id, categories in user_categories_map.items():
        user = users_by_id.get(user_id)
        if not user:
            continue
        for category in categories:
            category_to_users[category["category_name"]].append(user)

    if not category_to_users:
        log("No subscribed categories found.")
        return

    fetcher = NewsFetchService()
    summarizer = SummarizerService()
    translator = TranslateService()

    all_records: list[dict] = []
    for site_url in site_urls:
        log(f"Fetching from {site_url}")
        site_records = fetcher.fetch_from_site(site_url, limit_per_site=limit_per_site)
        log(f"  -> found {len(site_records)} article(s)")
        for record in site_records:
            record["link_norm"] = normalize_link(record.get("link", ""))
        all_records.extend(site_records)

    if not all_records:
        log("No articles collected from configured sites.")
        return

    all_records.sort(key=lambda record: record.get("published", ""), reverse=True)
    log(f"Collected before dedupe: {len(all_records)}")
    all_records = remove_duplicates(all_records)
    log(f"Collected after dedupe: {len(all_records)}")

    variants_map = build_language_variants_batch(
        records=all_records,
        allowed_categories=allowed_categories,
        summarizer=summarizer,
        translator=translator,
        batch_size=batch_size,
    )

    log(f"Ready variant groups for insert: {len(variants_map)}")

    total_records_seen = len(all_records)
    total_records_stored = 0
    total_user_groups = 0

    for record in all_records:
        link_norm = record.get("link_norm", "")
        variants = variants_map.get(link_norm)
        if not variants:
            continue

        category_name = variants["EN"].get("category_name", "")
        category_id = category_name_to_id.get(category_name)
        subscribed_users = category_to_users.get(category_name, [])
        news_date = parse_news_date(record.get("published", ""))

        if not category_id or not subscribed_users:
            continue

        for user in subscribed_users:
            total_user_groups += 1
            log(
                f"Inserting article for user {user.get('email', user['id'])} "
                f"in 3 languages under category {category_name}"
            )
            for lang_code, payload in variants.items():
                save_news_item_for_user(
                    image_url=payload.get("image_url"),
                    insight=payload.get("insight", ""),
                    keywords=payload.get("keywords", ""),
                    news_date=news_date,
                    news_lang=lang_code,
                    news_url=payload.get("link", record.get("link", "")),
                    summary=payload.get("summary", ""),
                    title=payload.get("title", ""),
                    category_id=category_id,
                    user_id=user["id"],
                )
                total_records_stored += 1

    log("\n=== FETCH COMPLETE ===")
    log(f"Total deduplicated records analyzed: {total_records_seen}")
    log(f"Total per-user article groups inserted: {total_user_groups}")
    log(f"Total user-specific inserts attempted: {total_records_stored}")


if __name__ == "__main__":
    main()
