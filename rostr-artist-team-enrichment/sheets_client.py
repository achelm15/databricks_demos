"""Google Sheets read/update helper.

Two auth modes:
  - "adc"     : Application Default Credentials (gcloud login). Local dev only.
  - "service" : GCP service-account JSON. The path comes from
                GOOGLE_APPLICATION_CREDENTIALS or, in a Databricks job,
                from a secret resolved by the caller.

The sheet schema this demo expects:
    A: Artist
    B: Agency
    C: Agent Name
    D: Management
    E: Mangement Contact   (the original sheet had this typo;
                            ensure_canonical_header() fixes it on the fly)
    F: Last Updated

A row "needs enrichment" when any of B/C/D/E is blank.
"""
from __future__ import annotations

import datetime as dt
import logging
from dataclasses import dataclass, field
from typing import Any

from google.auth.transport.requests import AuthorizedSession
from google.oauth2 import service_account
import google.auth

logger = logging.getLogger(__name__)

SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]

# Canonical column order. We rename the typo on first run so subsequent
# diffs against this list are stable.
HEADERS = ["Artist", "Agency", "Agent Name", "Management", "Management Contact", "Last Updated"]
COL_ARTIST = 0
COL_AGENCY = 1
COL_AGENT = 2
COL_MGMT = 3
COL_MGMT_CONTACT = 4
COL_UPDATED = 5

# Header strings we'll accept as already-correct or as the legacy typo.
HEADER_ALIASES = {
    "Mangement Contact": "Management Contact",  # original typo in the sheet
}


@dataclass
class ArtistRow:
    row_index: int          # 0-based row number in the sheet (row 0 is header)
    artist: str
    agency: str = ""
    agent_name: str = ""
    management: str = ""
    management_contact: str = ""
    last_updated: str = ""
    handle_override: str | None = None  # optional, only used if a 'Rostr Handle' column exists

    def needs_enrichment(self) -> bool:
        return not all([self.agency, self.agent_name, self.management, self.management_contact])

    def blank_columns(self) -> list[int]:
        out = []
        if not self.agency:             out.append(COL_AGENCY)
        if not self.agent_name:         out.append(COL_AGENT)
        if not self.management:         out.append(COL_MGMT)
        if not self.management_contact: out.append(COL_MGMT_CONTACT)
        return out


@dataclass
class CellUpdate:
    row_index: int            # 0-based; row 0 is header
    column_index: int         # 0-based; A=0
    value: str

    def to_a1(self, tab: str) -> str:
        col_letter = chr(ord("A") + self.column_index)
        return f"{tab}!{col_letter}{self.row_index + 1}"


class SheetsClient:
    def __init__(
        self,
        sheet_id: str,
        tab: str = "Sheet1",
        *,
        auth_mode: str = "adc",
        service_account_path: str | None = None,
        quota_project: str | None = None,
    ):
        self.sheet_id = sheet_id
        self.tab = tab
        self.quota_project = quota_project

        if auth_mode == "service":
            if not service_account_path:
                raise ValueError("auth_mode=service requires service_account_path")
            creds = service_account.Credentials.from_service_account_file(
                service_account_path, scopes=SCOPES
            )
        elif auth_mode == "adc":
            # google.auth.default() picks up gcloud Application Default Credentials.
            creds, _ = google.auth.default(scopes=SCOPES)
        else:
            raise ValueError(f"Unknown auth_mode={auth_mode!r}")

        self._http = AuthorizedSession(creds)
        if quota_project:
            self._http.headers["x-goog-user-project"] = quota_project

    # -------------------------------------------------------------- low-level
    def _url(self, path: str) -> str:
        return f"https://sheets.googleapis.com/v4/spreadsheets/{self.sheet_id}{path}"

    def _get(self, path: str, **params) -> dict[str, Any]:
        r = self._http.get(self._url(path), params=params or None)
        r.raise_for_status()
        return r.json()

    def _post(self, path: str, body: dict[str, Any], **params) -> dict[str, Any]:
        r = self._http.post(self._url(path), json=body, params=params or None)
        r.raise_for_status()
        return r.json()

    def _put(self, path: str, body: dict[str, Any], **params) -> dict[str, Any]:
        r = self._http.put(self._url(path), json=body, params=params or None)
        r.raise_for_status()
        return r.json()

    # ----------------------------------------------------------------- header
    def ensure_canonical_header(self) -> None:
        """Renames any legacy typo headers to the canonical form (idempotent)."""
        values = self.read_range(f"{self.tab}!A1:Z1").get("values") or [[]]
        if not values or not values[0]:
            logger.warning("Sheet %s tab %r has no header row.", self.sheet_id, self.tab)
            return
        header = values[0]
        new_header = [HEADER_ALIASES.get(h, h) for h in header]
        if new_header == header:
            return
        logger.info("Fixing header typos: %s -> %s", header, new_header)
        self._put(
            f"/values/{self.tab}!A1",
            {"values": [new_header]},
            valueInputOption="USER_ENTERED",
        )

    # ----------------------------------------------------------------- read
    def read_range(self, a1_range: str) -> dict[str, Any]:
        return self._get(f"/values/{a1_range}")

    def read_artists(self) -> list[ArtistRow]:
        data = self.read_range(f"{self.tab}!A1:Z1000").get("values") or []
        if not data:
            return []
        header = data[0]
        # Detect optional override column.
        try:
            handle_col = header.index("Rostr Handle")
        except ValueError:
            handle_col = None

        out: list[ArtistRow] = []
        for i, row in enumerate(data[1:], start=1):
            # row may be shorter than header if trailing cells are blank
            row = row + [""] * (max(len(header), 6) - len(row))
            artist = (row[COL_ARTIST] or "").strip()
            if not artist:
                continue
            out.append(
                ArtistRow(
                    row_index=i,
                    artist=artist,
                    agency=(row[COL_AGENCY] or "").strip(),
                    agent_name=(row[COL_AGENT] or "").strip(),
                    management=(row[COL_MGMT] or "").strip(),
                    management_contact=(row[COL_MGMT_CONTACT] or "").strip(),
                    last_updated=(row[COL_UPDATED] or "").strip() if len(row) > COL_UPDATED else "",
                    handle_override=(row[handle_col] or "").strip() if handle_col is not None else None,
                )
            )
        return out

    # ----------------------------------------------------------------- write
    def apply_updates(self, updates: list[CellUpdate]) -> int:
        """Batch-write a list of CellUpdate. Returns number of cells written."""
        if not updates:
            return 0
        body = {
            "valueInputOption": "USER_ENTERED",
            "data": [
                {"range": u.to_a1(self.tab), "values": [[u.value]]}
                for u in updates
            ],
        }
        result = self._post("/values:batchUpdate", body)
        return result.get("totalUpdatedCells", 0)


# ----------------------------------------------------------------- helpers
def now_iso_minute() -> str:
    """UTC timestamp truncated to the minute, for 'Last Updated' stamps."""
    return dt.datetime.now(dt.timezone.utc).replace(second=0, microsecond=0).isoformat()
