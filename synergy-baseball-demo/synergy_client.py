"""Client for the Synergy Sports Baseball external API.

Auth is OAuth2 client-credentials: exchange client_id/client_secret for a bearer token, then
every data route is ``POST /api/<entity>/filter`` returning ``{"result": [...], "totalRecords": N}``,
paged with ``skip``/``take``.

The API returns intermittent 5xx on otherwise-valid requests, and the bearer token expires after
about an hour. Both are handled centrally in ``_request``: transient failures are retried with
backoff, and an expired token is re-minted once. A run that paginates a large entity therefore
survives both a blip and a token expiry instead of silently landing a partial table.

Credentials are never hardcoded; the notebooks resolve them from a local ``.env`` or a Databricks
secret scope and pass them in.
"""
from __future__ import annotations

import time
from typing import Any

import requests

BASE_URL = "https://baseball.synergysportstech.com/external"
TOKEN_URL = "https://auth.synergysportstech.com/connect/token"
API_SCOPE = "api.baseball.external"
PAGE_SIZE = 1000

# Codes worth retrying: rate-limiting plus the transient server errors this API is prone to.
RETRY_STATUSES = {429, 500, 502, 503, 504}

# GET /api/<entity>/{id} returns the same schema as the matching /filter list item, so these are
# single-record lookups for enrichment or spot checks, not a bulk source.
LOOKUP_PATHS = {
    "teams": "/api/teams/{id}",
    "games": "/api/games/{id}",
    "players": "/api/players/{id}",
    "events": "/api/events/{id}",
    "leagues": "/api/leagues/{id}",
    "divisions": "/api/divisions/{id}",
    "conferences": "/api/conferences/{id}",
    "competitions": "/api/competitions/{id}",
    "venues": "/api/venues/{id}",
    "umpires": "/api/umpires/{id}",
    "practice_events": "/api/practice/events/{id}",
    "practice_sessions": "/api/practice/sessions/{id}",
}


class SynergyAPIError(RuntimeError):
    pass


class SynergyAPI:
    """Client for the Synergy Sports Baseball external API.

    >>> api = SynergyAPI(client_id, client_secret)        # token fetched on init
    >>> teams = api.filter("/api/teams/filter")           # auto-paginated -> list[dict]
    >>> games = api.get_games(min_date="2024-04-01", max_date="2024-04-07", season=2024)
    >>> one_team = api.get_by_id("teams", "T0001")        # single-record lookup -> dict
    """

    def __init__(self, client_id: str | None = None, client_secret: str | None = None,
                 *, access_token: str | None = None, timeout: int = 120, max_retries: int = 4):
        self.timeout = timeout
        self.max_retries = max_retries
        self.session = requests.Session()
        # Keep the credentials so an expired token can be re-minted mid-run. A pre-issued token
        # (e.g. copied from the Synergy Swagger UI) has no credentials behind it, so it can't be
        # refreshed once it expires.
        self._client_id = client_id
        self._client_secret = client_secret
        if access_token:
            self.token = access_token
        elif client_id and client_secret:
            self.token = self._fetch_token()
        else:
            raise SynergyAPIError("provide either access_token=, or both client_id and client_secret")
        self._set_auth_header()

    def _can_refresh(self) -> bool:
        return bool(self._client_id and self._client_secret)

    def _set_auth_header(self) -> None:
        self.session.headers.update(
            {"Authorization": f"Bearer {self.token}", "Content-Type": "application/json"}
        )

    def _fetch_token(self) -> str:
        for attempt in range(self.max_retries + 1):
            resp = requests.post(
                TOKEN_URL,
                data={"grant_type": "client_credentials", "client_id": self._client_id,
                      "client_secret": self._client_secret, "scope": API_SCOPE},
                timeout=self.timeout,
            )
            if resp.status_code == 200:
                return resp.json()["access_token"]
            if resp.status_code not in RETRY_STATUSES or attempt == self.max_retries:
                raise SynergyAPIError(
                    f"Synergy token request failed ({resp.status_code}): {resp.text[:200]}")
            time.sleep(2 ** attempt)
        raise SynergyAPIError("Synergy token request failed: retries exhausted")  # unreachable

    def _request(self, method: str, url: str, **kwargs: Any) -> requests.Response:
        """Single send path for every API call. Retries transient 5xx/429 with exponential
        backoff, and re-authenticates once if the token has expired (401). The caller inspects
        the returned response and raises on a non-200, so the request contract is unchanged."""
        kwargs.setdefault("timeout", self.timeout)
        reauthed = False
        for attempt in range(self.max_retries + 1):
            resp = self.session.request(method, url, **kwargs)
            if resp.status_code == 401 and not reauthed and self._can_refresh():
                self.token = self._fetch_token()
                self._set_auth_header()
                reauthed = True
                continue
            if resp.status_code not in RETRY_STATUSES or attempt == self.max_retries:
                return resp
            time.sleep(2 ** attempt)
        return resp

    def filter(self, path: str, body: dict | None = None, *, page_size: int = PAGE_SIZE,
               max_pages: int = 100_000) -> list[dict]:
        """POST a ``/api/<entity>/filter`` route, paging skip/take until every row is pulled.

        ``body`` is the static filter (e.g. ``{"season": 2024, "minDate": "..."}``); skip/take are
        added per page. Stops on a short/empty page or once ``skip`` reaches ``totalRecords``.
        """
        body = dict(body or {})
        url = BASE_URL + path
        rows: list[dict] = []
        skip = 0
        for _ in range(max_pages):
            r = self._request("POST", url, json={**body, "skip": skip, "take": page_size})
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

    def filter_by_ids(self, path: str, id_field: str, ids: list[str], *, batch_size: int = 50,
                      extra_body: dict | None = None, page_size: int = PAGE_SIZE) -> list[dict]:
        """Pull a route that requires id-scoping (the event-level and practice/events routes reject
        a date-only query with a 500). Batches ``ids`` into ``id_field`` and concatenates the pages.

        >>> api.filter_by_ids("/api/practice/events/filter", "practiceSessionIds", ids, batch_size=50)
        """
        extra = dict(extra_body or {})
        rows: list[dict] = []
        for i in range(0, len(ids), batch_size):
            chunk = ids[i:i + batch_size]
            if not chunk:
                continue
            rows.extend(self.filter(path, {**extra, id_field: chunk}, page_size=page_size))
        return rows

    def get_teams(self, **filt: Any) -> list[dict]:
        """All teams visible to your credentials."""
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

    def get_by_id(self, entity: str, record_id: str) -> dict:
        """Fetch one record via ``GET /api/<entity>/{id}``. Returns the dict, or ``{}`` on 404."""
        if entity not in LOOKUP_PATHS:
            raise KeyError(f"no lookup path for {entity!r}; known: {sorted(LOOKUP_PATHS)}")
        url = BASE_URL + LOOKUP_PATHS[entity].format(id=record_id)
        r = self._request("GET", url)
        if r.status_code == 404:
            return {}
        if r.status_code != 200:
            raise SynergyAPIError(f"GET {url} failed ({r.status_code}): {r.text[:200]}")
        return r.json()

    def sign_videos(self, urls: list[str]) -> dict:
        """``POST /api/videos/sign`` — exchange video URLs for signed playback URLs."""
        url = BASE_URL + "/api/videos/sign"
        r = self._request("POST", url, json={"urls": list(urls)})
        if r.status_code != 200:
            raise SynergyAPIError(f"POST /api/videos/sign failed ({r.status_code}): {r.text[:200]}")
        return r.json()
