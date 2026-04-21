from __future__ import annotations

from dotenv import load_dotenv

from scripts.fetch_and_store_news import main as fetch_and_store_news_main
from scripts.run_daily_news import main as run_daily_news_main


def main() -> None:
    load_dotenv()
    print("\n=== PIPELINE STARTED ===", flush=True)
    print("Step 1/2: Fetching, analyzing, translating, and storing news...", flush=True)
    fetch_and_store_news_main()
    print("\nStep 2/2: Building digests and sending emails...", flush=True)
    run_daily_news_main()
    print("\n=== PIPELINE FINISHED ===", flush=True)


if __name__ == "__main__":
    main()