from __future__ import annotations

import requests


class NewsSourcesClient:
    def fetch_json(self, url: str, timeout: int = 30) -> dict:
        response = requests.get(url, timeout=timeout)
        response.raise_for_status()
        return response.json()
