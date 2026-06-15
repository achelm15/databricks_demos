"""Synergy Sports Baseball external API client.

Auth is **OAuth2 client-credentials**: exchange client_id/client_secret for a bearer token, then every
data route is ``POST /api/<entity>/filter`` returning ``{"result": [...], "totalRecords": N}``. We page
with ``skip``/``take`` until all rows are pulled.

Ported from the agnostic ``mlb_pipelines`` Synergy accelerator (src/synergy/_lib.py) into a demo-friendly
class.

Credentials are NEVER hardcoded — the notebooks resolve them from a local ``.env`` or a Databricks secret
scope and pass them in.
"""
from __future__ import annotations

from typing import Any

import requests

BASE_URL = "https://baseball.synergysportstech.com/external"
TOKEN_URL = "https://auth.synergysportstech.com/connect/token"
API_SCOPE = "api.baseball.external"
PAGE_SIZE = 1000


class SynergyAPIError(RuntimeError):
    pass


class SynergyAPI:
    """High-level client for the Synergy Sports Baseball external API.

    >>> api = SynergyAPI(client_id, client_secret)        # OAuth token fetched on init
    >>> teams = api.filter("/api/teams/filter")           # auto-paginated -> list[dict]
    >>> games = api.get_games(min_date="2024-04-01", max_date="2024-04-07", season=2024)
    """

    def __init__(self, client_id: str, client_secret: str, *, timeout: int = 120):
        self.timeout = timeout
        self.session = requests.Session()
        self.token = self._get_token(client_id, client_secret)
        self.session.headers.update(
            {"Authorization": f"Bearer {self.token}", "Content-Type": "application/json"}
        )

    # ------------------------------------------------------------------ auth
    def _get_token(self, client_id: str, client_secret: str) -> str:
        resp = requests.post(
            TOKEN_URL,
            data={"grant_type": "client_credentials", "client_id": client_id,
                  "client_secret": client_secret, "scope": API_SCOPE},
            timeout=self.timeout,
        )
        if resp.status_code != 200:
            raise SynergyAPIError(f"Synergy token request failed ({resp.status_code}): {resp.text[:200]}")
        return resp.json()["access_token"]

    # ----------------------------------------------------------------- core
    def filter(self, path: str, body: dict | None = None, *, page_size: int = PAGE_SIZE,
               max_pages: int = 100_000) -> list[dict]:
        """POST ``path`` (a ``/api/<entity>/filter`` route), paging skip/take until every row is pulled.

        ``body`` is the static filter (e.g. ``{"season": 2024, "minDate": "..."}``); ``skip``/``take`` are
        added per page. Stops on a short/empty page or once ``skip`` reaches ``totalRecords``.
        """
        body = dict(body or {})
        url = BASE_URL + path
        rows: list[dict] = []
        skip = 0
        for _ in range(max_pages):
            r = self.session.post(url, json={**body, "skip": skip, "take": page_size}, timeout=self.timeout)
            if r.status_code != 200:
                raise SynergyAPIError(f"POST {path} failed ({r.status_code}): {r.text[:200]}")
            payload = r.json()
            page = payload.get("result") or []
            rows.extend(page)
            total = payload.get("totalRecords")
            skip += page_size
            if not page or len(page) < page_size or (total is not None and skip >= total):
                break
        return rows

    # --------------------------------------------------------- convenience
    # Thin wrappers so the notebooks read clearly. Add more as you fan out (players, events, venues, ...).
    def get_teams(self, **filt: Any) -> list[dict]:
        """Reference entity — all teams visible to your credentials."""
        return self.filter("/api/teams/filter", filt or None)

    def get_games(self, *, min_date: str | None = None, max_date: str | None = None,
                  season: int | None = None, **filt: Any) -> list[dict]:
        """Games, optionally scoped by date window (minDate/maxDate, inclusive ISO) and/or season."""
        body: dict[str, Any] = dict(filt)
        if min_date:
            body["minDate"] = min_date
        if max_date:
            body["maxDate"] = max_date
        if season is not None:
            body["season"] = season
        return self.filter("/api/games/filter", body or None)
