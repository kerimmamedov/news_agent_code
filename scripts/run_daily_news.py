from __future__ import annotations

import os
import traceback

from dotenv import load_dotenv

from app.db.repositories import save_sent_article
from app.services.email_service import render_digest_email, send_email
from app.services.newsletter_service import build_all_user_digests


def log(message: str) -> None:
    print(message, flush=True)


def main():
    load_dotenv()

    max_articles_raw = os.getenv("MAX_ARTICLES_PER_USER", "").strip()
    max_articles = int(max_articles_raw) if max_articles_raw else 50
    dry_run = os.getenv("DRY_RUN", "true").lower() == "true"

    log("=== RUN DAILY NEWS ===")
    log(f"max_articles={max_articles}")
    log(f"dry_run={dry_run}")

    digests = build_all_user_digests(max_articles=max_articles)

    if not digests:
        log("No digests to send.")
        return

    log(f"Prepared digests for {len(digests)} user(s).")

    for digest in digests:
        email = digest["email"]
        subject = digest["subject"]
        articles = digest["articles"]

        log("\n----------------------------------------")
        log(f"User: {digest['username']} | {email}")
        log(f"Articles: {len(articles)}")

        try:
            html_body, text_body = render_digest_email(digest)

            if dry_run:
                log("[DRY RUN] Email not sent.")
                for article in articles:
                    log(f" - {article['title']} | {article['news_url']}")
                continue

            log("Sending email...")
            send_email(
                to_email=email,
                subject=subject,
                html_body=html_body,
                text_body=text_body,
            )

            log("Email sent successfully.")

            for article in articles:
                save_sent_article(
                    article_link=article["news_url"],
                    article_title=article["title"],
                    user_email=email,
                )

            log("sent_articles log saved.")

        except Exception as exc:
            log(f"Failed for {email}: {exc}")
            traceback.print_exc()


if __name__ == "__main__":
    main()