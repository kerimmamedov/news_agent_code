from __future__ import annotations

from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from urllib.parse import urljoin, urlparse

import feedparser
import requests
from bs4 import BeautifulSoup
from zoneinfo import ZoneInfo


class NewsFetchService:
    FEED_OVERRIDES: dict[str, str | dict[str, str]] = {
        "https://www.equipmentfa.com/": "https://www.equipmentfa.com/rss/feeds/latestnews.xml",
        "https://www.abladvisor.com/": "https://www.abladvisor.com/rss/feeds/latestnews.xml",
        "https://www.financeasia.com/": "https://www.financeasia.com/rss/latest",
        "https://www.caixinglobal.com/": "https://feedly.com/i/subscription/feed%2Fhttps%3A%2F%2Fgateway.caixin.com%2Fapi%2Fdata%2Fglobal%2FfeedlyRss.xml",
        "https://www.disruptionbanking.com/": "https://www.disruptionbanking.com/feed/",
        "https://www.connectingafrica.com/fintech": "https://www.connectingafrica.com/rss.xml",
        "https://www.crowdfundinsider.com/": "https://www.crowdfundinsider.com/feed/",
        "https://thefintechtimes.com/": "https://thefintechtimes.com/feed/",
        "https://www.finextra.com/": "https://www.finextra.com/rss/channel.aspx?channel=ai",
        "https://asfact.ru/news": "https://asfact.ru/news/feed/",
        "https://www.cnbc.com/fintech": {
            "feed": "https://www.cnbc.com/id/100003114/device/rss/rss.html",
            "scope": "broad",
        },
    }

    def __init__(self) -> None:
        self.session = requests.Session()
        self.session.headers.update(
            {
                "User-Agent": (
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/123.0.0.0 Safari/537.36"
                )
            }
        )
        self.baku_tz = ZoneInfo("Asia/Baku")

    def fetch_from_site(self, site_url: str, limit_per_site: int = 5) -> list[dict]:
        normalized_site = self._norm(site_url)
        if not normalized_site:
            return []

        rss_records = self._fetch_rss_records(normalized_site, limit_per_site)
        if rss_records:
            return self._dedupe_records(rss_records)[:limit_per_site]

        wp_records = self._fetch_wordpress_records(normalized_site, limit_per_site)
        if wp_records:
            return self._dedupe_records(wp_records)[:limit_per_site]

        return []

    def _fetch_rss_records(self, site_url: str, limit_per_site: int) -> list[dict]:
        records: list[dict] = []
        for feed_url in self._find_feed_urls(site_url):
            try:
                response = self.session.get(feed_url, timeout=10)
                response.raise_for_status()
            except Exception:
                continue

            try:
                parsed = feedparser.parse(response.text)
            except Exception:
                continue

            for entry in parsed.entries or []:
                if len(records) >= limit_per_site:
                    break

                published_dt = self._extract_entry_datetime(entry)
                if published_dt is None or published_dt.astimezone(self.baku_tz).date() != self._today_baku():
                    continue

                title = self._clean_html(entry.get("title", "")).strip()
                link = (entry.get("link", "") or "").strip()
                summary = self._clean_html(
                    entry.get("summary", "") or entry.get("description", "")
                ).strip()
                image_url = self._extract_image_from_entry(entry)

                if not title or not link:
                    continue

                records.append(
                    {
                        "feed": feed_url,
                        "title": title,
                        "link": link,
                        "summary": summary,
                        "published": published_dt.astimezone(self.baku_tz).isoformat(),
                        "image_url": image_url,
                    }
                )

            if records:
                break

        return records

    def _fetch_wordpress_records(self, site_url: str, limit_per_site: int) -> list[dict]:
        api_url = f"{site_url.rstrip('/')}/wp-json/wp/v2/posts?per_page={limit_per_site}"

        try:
            response = self.session.get(api_url, timeout=10)
            response.raise_for_status()
            posts = response.json()
        except Exception:
            return []

        if not isinstance(posts, list):
            return []

        records: list[dict] = []
        today = self._today_baku()

        for post in posts:
            if len(records) >= limit_per_site:
                break

            title_obj = post.get("title") or {}
            if isinstance(title_obj, dict):
                title = self._clean_html(title_obj.get("rendered", "")).strip()
            else:
                title = self._clean_html(str(title_obj)).strip()

            link = (post.get("link") or "").strip()
            if not title or not link:
                continue

            published_dt = self._extract_wp_datetime(post)
            if published_dt is None or published_dt.astimezone(self.baku_tz).date() != today:
                continue

            excerpt_obj = post.get("excerpt") or {}
            if isinstance(excerpt_obj, dict):
                summary_html = excerpt_obj.get("rendered", "") or ""
            else:
                summary_html = str(excerpt_obj or "")

            summary = self._clean_html(summary_html)
            if not summary:
                content_obj = post.get("content") or {}
                if isinstance(content_obj, dict):
                    summary = self._clean_html(content_obj.get("rendered", "") or "")[:500]
                else:
                    summary = self._clean_html(str(content_obj or ""))[:500]

            records.append(
                {
                    "feed": api_url,
                    "title": title,
                    "link": link,
                    "summary": summary,
                    "published": published_dt.astimezone(self.baku_tz).isoformat(),
                    "image_url": self._extract_image_from_wp_post(post),
                }
            )

        return records

    def _find_feed_urls(self, site_url: str) -> list[str]:
        site_norm = self._norm(site_url)

        direct = self.FEED_OVERRIDES.get(site_norm)
        if direct:
            feed_url = self._override_to_feed_url(direct)
            return [feed_url] if feed_url else []

        for base_url, override_value in self.FEED_OVERRIDES.items():
            base_norm = self._norm(base_url)
            if site_norm == base_norm or site_norm.startswith(f"{base_norm}/"):
                feed_url = self._override_to_feed_url(override_value)
                return [feed_url] if feed_url else []

        try:
            response = self.session.get(site_url, timeout=10)
            response.raise_for_status()
        except Exception:
            return []

        soup = BeautifulSoup(response.text, "html.parser")
        feeds: list[str] = []
        seen: set[str] = set()

        for link in soup.find_all("link", href=True):
            type_attr = (link.get("type") or "").lower()
            rel_attr = " ".join(link.get("rel", [])).lower()
            if "alternate" not in rel_attr:
                continue
            if "rss" not in type_attr and "atom" not in type_attr and "xml" not in type_attr:
                continue

            feed_url = urljoin(site_url, link["href"])
            if feed_url not in seen:
                seen.add(feed_url)
                feeds.append(feed_url)

        return feeds

    def _extract_entry_datetime(self, entry) -> datetime | None:
        for attr_name in ("published_parsed", "updated_parsed"):
            parsed_value = entry.get(attr_name)
            if parsed_value:
                try:
                    return datetime(*parsed_value[:6], tzinfo=timezone.utc)
                except Exception:
                    pass

        for attr_name in ("published", "updated", "created"):
            raw_value = entry.get(attr_name)
            if not raw_value:
                continue
            try:
                return parsedate_to_datetime(raw_value)
            except Exception:
                continue

        return None

    def _extract_wp_datetime(self, post: dict) -> datetime | None:
        for field_name in ("date_gmt", "date"):
            raw_value = post.get(field_name)
            if not raw_value:
                continue
            try:
                normalized = raw_value.replace("Z", "+00:00")
                parsed = datetime.fromisoformat(normalized)
                if parsed.tzinfo is None:
                    if field_name == "date_gmt":
                        parsed = parsed.replace(tzinfo=timezone.utc)
                    else:
                        parsed = parsed.replace(tzinfo=self.baku_tz)
                return parsed
            except Exception:
                continue

        return None

    def _extract_image_from_entry(self, entry) -> str | None:
        media_content = entry.get("media_content", [])
        if isinstance(media_content, list):
            for item in media_content:
                image_url = item.get("url")
                if image_url:
                    return image_url

        media_thumbnail = entry.get("media_thumbnail", [])
        if isinstance(media_thumbnail, list):
            for item in media_thumbnail:
                image_url = item.get("url")
                if image_url:
                    return image_url

        enclosures = entry.get("enclosures", [])
        if isinstance(enclosures, list):
            for item in enclosures:
                mime_type = item.get("type", "")
                if mime_type.startswith("image/") and item.get("url"):
                    return item["url"]

        html_value = ""
        content_items = getattr(entry, "content", None)
        if content_items:
            try:
                html_value = content_items[0].get("value", "") or ""
            except Exception:
                html_value = ""
        if not html_value:
            html_value = entry.get("summary", "") or ""

        if html_value:
            soup = BeautifulSoup(html_value, "html.parser")
            image = soup.find("img")
            if image and image.get("src"):
                return image["src"]

        return None

    def _extract_image_from_wp_post(self, post: dict) -> str | None:
        featured = post.get("jetpack_featured_media_url")
        if featured:
            return featured

        yoast = post.get("yoast_head_json")
        if isinstance(yoast, dict):
            og_images = yoast.get("og_image")
            if isinstance(og_images, list) and og_images:
                first = og_images[0]
                if isinstance(first, dict) and first.get("url"):
                    return first["url"]

        html_value = ""
        content_obj = post.get("content") or {}
        excerpt_obj = post.get("excerpt") or {}

        if isinstance(content_obj, dict):
            html_value = content_obj.get("rendered", "") or ""
        if not html_value and isinstance(excerpt_obj, dict):
            html_value = excerpt_obj.get("rendered", "") or ""

        if html_value:
            soup = BeautifulSoup(html_value, "html.parser")
            image = soup.find("img")
            if image and image.get("src"):
                return image["src"]

        return None

    def _clean_html(self, value: str) -> str:
        if not value:
            return ""
        soup = BeautifulSoup(value, "html.parser")
        return soup.get_text(" ", strip=True)

    def _dedupe_records(self, records: list[dict]) -> list[dict]:
        deduped: dict[str, dict] = {}

        for record in records:
            link = self._norm(record.get("link", ""))
            if not link:
                continue
            if link not in deduped:
                deduped[link] = record

        return list(deduped.values())

    def _today_baku(self):
        return datetime.now(self.baku_tz).date()

    def _norm(self, value: str) -> str:
        return (value or "").strip().rstrip("/")

    def _override_to_feed_url(self, value: str | dict[str, str]) -> str | None:
        if isinstance(value, dict):
            return value.get("feed")
        return value
