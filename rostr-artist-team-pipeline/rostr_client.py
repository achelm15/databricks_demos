"""ROSTR.cc API client.

The web login form is gated by Cloudflare Turnstile + Castle.io fraud
fingerprinting, but the underlying JSON API only requires email + password —
the fraud token is enforced at the web origin only. So we can skip headless
browsers entirely and just use `requests`.

Endpoints (reverse-engineered from the SPA bundle, all confirmed working):
    POST /v1/auth/rostr             login with {email, password} -> sets rack.session
    GET  /v1/auth/me                cookie probe
    GET  /v1/artist/{handle}        artist detail (rostrId, name, ...)
    GET  /v1/artist/{handle}/team/{ROLE}
                                    list of {company, team:[{people}]} for the role
"""
from __future__ import annotations

import json
import logging
import re
import time
import unicodedata
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import requests

logger = logging.getLogger(__name__)

ROSTR_WEB = "https://www.rostr.cc"
ROSTR_API = "https://api.rostr.cc"
SESSION_COOKIE = "rack.session"

ROLE_MANAGEMENT = "MANAGEMENT"
ROLE_AGENCY = "AGENCY"


class RostrAuthError(RuntimeError):
    pass


class RostrAPIError(RuntimeError):
    pass


@dataclass
class TeamContact:
    """One person assigned to an artist on rostr.cc."""

    role: str            # MANAGEMENT | AGENCY (the company role)
    company: str         # e.g. "WME", "Mookie Singerman"
    person_name: str | None = None   # e.g. "Kirk Sommer"
    person_title: str | None = None  # e.g. "AGENT", "MANAGER"
    person_email: str | None = None
    person_phone: str | None = None


@dataclass
class ArtistTeam:
    handle: str
    rostr_id: str
    name: str
    contacts: list[TeamContact] = field(default_factory=list)
    raw_artist: dict[str, Any] | None = None
    raw_teams: dict[str, Any] = field(default_factory=dict)  # {role: payload}

    def by_role(self, role: str) -> list[TeamContact]:
        return [c for c in self.contacts if c.role == role]


def slugify(name: str) -> str:
    """'Olivia Rodrigo' -> 'oliviarodrigo' to match rostr.cc handle pattern."""
    n = unicodedata.normalize("NFKD", name).encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9]", "", n.lower())


class RostrClient:
    def __init__(
        self,
        username: str,
        password: str,
        *,
        cookie_path: str | Path | None = ".cookie.json",
        timeout: int = 20,
        rate_limit_seconds: float = 0.5,
    ):
        self.username = username
        self.password = password
        self.cookie_path = Path(cookie_path) if cookie_path else None
        self.timeout = timeout
        self.rate_limit_seconds = rate_limit_seconds
        self._last_request_at = 0.0
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": (
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36"
            ),
            "Accept": "application/json, text/plain, */*",
            "Origin": ROSTR_WEB,
            "Referer": f"{ROSTR_WEB}/",
            "Content-Type": "application/json",
        })

    # ------------------------------------------------------------------ auth
    def authenticate(self) -> None:
        if self._load_cached_cookie() and self._cookie_works():
            logger.info("Using cached rostr.cc session cookie.")
            return
        self._login()
        self._save_cookie()

    def _login(self) -> None:
        logger.info("Logging in to rostr.cc as %s ...", self.username)
        r = self.session.post(
            f"{ROSTR_API}/v1/auth/rostr",
            json={"email": self.username, "password": self.password},
            timeout=self.timeout,
        )
        if r.status_code != 201:
            raise RostrAuthError(f"login failed ({r.status_code}): {r.text[:200]}")
        if not self.session.cookies.get(SESSION_COOKIE):
            raise RostrAuthError("login returned 201 but no rack.session cookie was set")

    def _load_cached_cookie(self) -> bool:
        if not self.cookie_path or not self.cookie_path.exists():
            return False
        try:
            data = json.loads(self.cookie_path.read_text())
        except Exception as e:
            logger.warning("Could not parse %s: %s", self.cookie_path, e)
            return False
        cookie = data.get(SESSION_COOKIE)
        if not cookie:
            return False
        self.session.cookies.set(SESSION_COOKIE, cookie, domain=".rostr.cc")
        return True

    def _save_cookie(self) -> None:
        if not self.cookie_path:
            return
        cookie = self.session.cookies.get(SESSION_COOKIE)
        if not cookie:
            return
        self.cookie_path.parent.mkdir(parents=True, exist_ok=True)
        self.cookie_path.write_text(json.dumps({SESSION_COOKIE: cookie}))

    def _cookie_works(self) -> bool:
        try:
            r = self.session.get(f"{ROSTR_API}/v1/auth/me", timeout=self.timeout)
        except requests.RequestException:
            return False
        return r.status_code == 200

    # ---------------------------------------------------------------- requests
    def _throttle(self) -> None:
        delta = time.monotonic() - self._last_request_at
        if delta < self.rate_limit_seconds:
            time.sleep(self.rate_limit_seconds - delta)
        self._last_request_at = time.monotonic()

    def _get(self, path: str) -> Any:
        self._throttle()
        r = self.session.get(f"{ROSTR_API}{path}", timeout=self.timeout)
        if r.status_code in (401, 403):
            raise RostrAuthError(f"{r.status_code} on {path}: {r.text[:200]}")
        if r.status_code == 404:
            raise RostrAPIError(f"404 on {path}")
        r.raise_for_status()
        return r.json()

    # ------------------------------------------------------------------ data
    def get_artist(self, handle: str) -> dict[str, Any]:
        return self._get(f"/v1/artist/{handle}")

    def get_team(self, handle: str, role: str) -> list[dict[str, Any]]:
        """`/v1/artist/{handle}/team/{role}` — list of {company, team:[{people}]}."""
        data = self._get(f"/v1/artist/{handle}/team/{role}")
        return data if isinstance(data, list) else []

    def lookup_artist_team(
        self,
        name: str,
        *,
        handle_override: str | None = None,
    ) -> ArtistTeam:
        """End-to-end: name → handle → artist + team(MANAGEMENT) + team(AGENCY) → ArtistTeam."""
        handle = handle_override or slugify(name)
        try:
            artist = self.get_artist(handle)
        except RostrAPIError as e:
            raise RostrAPIError(
                f"Could not find artist {name!r} (slug={handle!r}): {e}. "
                f"Try setting an explicit Rostr Handle column."
            )

        rostr_id = artist.get("rostrId") or artist.get("rostr_id") or handle
        teams: dict[str, list[dict]] = {}
        contacts: list[TeamContact] = []

        for role in (ROLE_MANAGEMENT, ROLE_AGENCY):
            try:
                payload = self.get_team(handle, role)
            except RostrAPIError:
                payload = []
            teams[role] = payload
            contacts.extend(self._extract_contacts(role, payload))

        return ArtistTeam(
            handle=handle,
            rostr_id=str(rostr_id),
            name=artist.get("name") or name,
            contacts=contacts,
            raw_artist=artist,
            raw_teams=teams,
        )

    @staticmethod
    def _extract_contacts(role: str, payload: list[dict[str, Any]]) -> list[TeamContact]:
        """Walk the per-role response and produce one TeamContact per artist-specific person.

        Each entry in `payload` has:
            company   : metadata about the company (incl. ALL its employees in `people`)
            team      : list of {people:[...]} describing the people assigned to THIS artist

        We use `team[*].people[*]`, not `company.people`, so we only get the
        agent/manager actually working with this artist.
        """
        out: list[TeamContact] = []
        for entry in payload:
            company = (entry.get("company") or {})
            company_name = company.get("name") or ""
            people: list[dict] = []
            for group in (entry.get("team") or []):
                people.extend(group.get("people") or [])
            if not people:
                # Company is on the artist's team but no specific person is named.
                # Record the company so we don't drop it from the sheet.
                out.append(TeamContact(role=role, company=company_name))
                continue
            for person in people:
                out.append(TeamContact(
                    role=role,
                    company=company_name,
                    person_name=person.get("name"),
                    person_title=person.get("role"),
                    person_email=person.get("email"),
                    person_phone=person.get("phone"),
                ))
        return out
