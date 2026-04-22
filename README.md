# News Agent

Notebook logic converted into a server-friendly Python project for Ubuntu deployment.

## What this project does
- Connects to PostgreSQL
- Loads categories, subscribed users, and sites from the database
- Fetches today's articles from RSS and WordPress JSON feeds
- Uses OpenAI to classify, summarize, and enrich articles in English
- Translates selected article content to Azerbaijani and Persian
- Stores user-specific news rows in PostgreSQL
- Builds and sends email digests
- Logs sent links into `sent_articles`

## Main entrypoints
- `python run.py`
  Runs the full notebook-style pipeline end to end.
- `python -m scripts.fetch_and_store_news`
  Fetches, analyzes, translates, and stores today's news.
- `python -m scripts.run_daily_news`
  Builds user digests from stored news and sends the emails.
- `python -m scripts.notebook_pipeline`
  Same full flow as `run.py`, added as the plain Python replacement for the notebook.

## Quick start

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
python -m scripts.test_db_connection
python run.py
```

## Windows local run

If you are running the project locally on Windows:

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\.venv\Scripts\Activate.ps1
python -m scripts.test_db_connection
.\run_news_agent.bat
```

To create Windows Task Scheduler jobs for `08:00` and `16:00`:

```powershell
.\schedule_news_agent_tasks.bat
```

The local batch run writes logs under:

```powershell
logs\
```

## Ubuntu scheduler

If you want the full pipeline to run automatically on Ubuntu at `08:00` and `16:00` Baku time:

```bash
chmod +x run_news_agent.sh install_news_agent_cron.sh
./install_news_agent_cron.sh
```

You can then verify the cron entries with:

```bash
crontab -l
```

The run logs will be written under:

```bash
logs/
```

## Ubuntu / local database note
If PostgreSQL is on the same Ubuntu server, set your `.env` roughly like this:

```bash
DB_HOST=127.0.0.1
DB_PORT=5432
DB_NAME=your_db_name
DB_USER=your_db_user
DB_PASSWORD=your_db_password
DB_SSLMODE=prefer
```

## Useful environment variables
- `MAX_SITES=0`
  `0` means process all sites.
- `FETCH_LIMIT_PER_SITE=5`
  Limits how many articles are taken per site.
- `BATCH_SIZE=5`
  OpenAI batch size for analyze/translate requests.
- `MAX_ARTICLES_PER_USER=50`
  Max number of articles included per user digest.
- `DRY_RUN=true`
  Shows the digest flow without sending emails.

## Database note
Ensure the `news.news_lang` check constraint allows `FA` in addition to the existing language codes.
