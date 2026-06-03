"""
nba_helpers.py — pure-Python reference utilities for the basketball-reference-waf demo.

Two things here are *reused at runtime* by the notebooks:

  * ``eastern_game_date(...)`` — used by ``01_ingest`` to stamp Basketball Reference's
    US/Eastern calendar game-date onto every scraped record. ``season_schedule`` returns
    ``start_time`` as timezone-aware UTC, but Basketball Reference files each game (and its
    box score) under the *Eastern* date, so a 10:30pm-ET tip-off must not roll to the next
    UTC day. Stamping the Eastern date at ingest time keeps the bronze->silver join tz-safe.

  * ``TEAM_METADATA`` / ``team_abbreviation`` / ``team_conference`` — used by ``04_gold``
    to build ``dim_team``.

The Four Factors functions are the **reference implementation** (Dean Oliver's four
factors of basketball success: shooting, turnovers, rebounding, free throws). The silver
notebook (``03``) computes the same quantities as Spark SQL for scale — keep the two in
sync. The scalar versions here are trivial to read and unit-test (see ``__main__``).
"""
from __future__ import annotations

from datetime import date, datetime
from zoneinfo import ZoneInfo

_EASTERN = ZoneInfo("America/New_York")
_UTC = ZoneInfo("UTC")


# --------------------------------------------------------------------------------------
# Time
# --------------------------------------------------------------------------------------
def eastern_game_date(start_time: datetime) -> date:
    """Return Basketball Reference's calendar (US/Eastern) date for a game tip-off.

    ``start_time`` from ``season_schedule`` is timezone-aware UTC. If a naive datetime is
    passed it is assumed to be UTC.
    """
    if start_time.tzinfo is None:
        start_time = start_time.replace(tzinfo=_UTC)
    return start_time.astimezone(_EASTERN).date()


# --------------------------------------------------------------------------------------
# Four Factors (per-team game totals in; rates out). None on divide-by-zero.
# --------------------------------------------------------------------------------------
def effective_field_goal_pct(made_fg: float, made_3p: float, attempted_fg: float):
    """eFG% = (FGM + 0.5 * 3PM) / FGA  — shooting, the most important factor."""
    return (made_fg + 0.5 * made_3p) / attempted_fg if attempted_fg else None


def turnover_pct(turnovers: float, attempted_fg: float, attempted_ft: float):
    """TOV% = TOV / (FGA + 0.44 * FTA + TOV)  — taking care of the ball."""
    denom = attempted_fg + 0.44 * attempted_ft + turnovers
    return turnovers / denom if denom else None


def offensive_rebound_pct(off_reb: float, opp_def_reb: float):
    """ORB% = ORB / (ORB + opponent DRB)  — second-chance opportunities."""
    denom = off_reb + opp_def_reb
    return off_reb / denom if denom else None


def free_throw_rate(made_ft: float, attempted_fg: float):
    """FT rate = FTM / FGA  — getting to the line and converting (Basketball Reference)."""
    return made_ft / attempted_fg if attempted_fg else None


def possessions(
    attempted_fg: float, attempted_ft: float, off_reb: float, turnovers: float,
    opp_attempted_fg: float, opp_attempted_ft: float, opp_off_reb: float, opp_turnovers: float,
):
    """Estimated possessions (averaged over both teams' tempo-free estimates)."""
    team = attempted_fg + 0.44 * attempted_ft - off_reb + turnovers
    opp = opp_attempted_fg + 0.44 * opp_attempted_ft - opp_off_reb + opp_turnovers
    return 0.5 * (team + opp)


def offensive_rating(points: float, poss: float):
    """Points scored per 100 possessions."""
    return 100.0 * points / poss if poss else None


# --------------------------------------------------------------------------------------
# Team reference data — keyed by the basketball_reference_web_scraper Team enum *value*
# string, so it joins directly to the scraped data. (abbreviation, conference, division)
# 30 current franchises + historical names the scraper can emit, so dim_team is complete.
# --------------------------------------------------------------------------------------
TEAM_METADATA = {
    "ATLANTA HAWKS": ("ATL", "East", "Southeast"),
    "BOSTON CELTICS": ("BOS", "East", "Atlantic"),
    "BROOKLYN NETS": ("BRK", "East", "Atlantic"),
    "CHARLOTTE HORNETS": ("CHO", "East", "Southeast"),
    "CHICAGO BULLS": ("CHI", "East", "Central"),
    "CLEVELAND CAVALIERS": ("CLE", "East", "Central"),
    "DALLAS MAVERICKS": ("DAL", "West", "Southwest"),
    "DENVER NUGGETS": ("DEN", "West", "Northwest"),
    "DETROIT PISTONS": ("DET", "East", "Central"),
    "GOLDEN STATE WARRIORS": ("GSW", "West", "Pacific"),
    "HOUSTON ROCKETS": ("HOU", "West", "Southwest"),
    "INDIANA PACERS": ("IND", "East", "Central"),
    "LOS ANGELES CLIPPERS": ("LAC", "West", "Pacific"),
    "LOS ANGELES LAKERS": ("LAL", "West", "Pacific"),
    "MEMPHIS GRIZZLIES": ("MEM", "West", "Southwest"),
    "MIAMI HEAT": ("MIA", "East", "Southeast"),
    "MILWAUKEE BUCKS": ("MIL", "East", "Central"),
    "MINNESOTA TIMBERWOLVES": ("MIN", "West", "Northwest"),
    "NEW ORLEANS PELICANS": ("NOP", "West", "Southwest"),
    "NEW YORK KNICKS": ("NYK", "East", "Atlantic"),
    "OKLAHOMA CITY THUNDER": ("OKC", "West", "Northwest"),
    "ORLANDO MAGIC": ("ORL", "East", "Southeast"),
    "PHILADELPHIA 76ERS": ("PHI", "East", "Atlantic"),
    "PHOENIX SUNS": ("PHO", "West", "Pacific"),
    "PORTLAND TRAIL BLAZERS": ("POR", "West", "Northwest"),
    "SACRAMENTO KINGS": ("SAC", "West", "Pacific"),
    "SAN ANTONIO SPURS": ("SAS", "West", "Southwest"),
    "TORONTO RAPTORS": ("TOR", "East", "Atlantic"),
    "UTAH JAZZ": ("UTA", "West", "Northwest"),
    "WASHINGTON WIZARDS": ("WAS", "East", "Southeast"),
    # Historical / relocated names the scraper's Team enum can still emit.
    "KANSAS CITY KINGS": ("KCK", "West", "Historical"),
    "CHARLOTTE BOBCATS": ("CHA", "East", "Historical"),
    "NEW JERSEY NETS": ("NJN", "East", "Historical"),
    "NEW ORLEANS HORNETS": ("NOH", "West", "Historical"),
    "NEW ORLEANS/OKLAHOMA CITY HORNETS": ("NOK", "West", "Historical"),
    "SEATTLE SUPERSONICS": ("SEA", "West", "Historical"),
    "ST. LOUIS HAWKS": ("STL", "East", "Historical"),
    "VANCOUVER GRIZZLIES": ("VAN", "West", "Historical"),
    "WASHINGTON BULLETS": ("WSB", "East", "Historical"),
}


def team_abbreviation(team: str) -> str:
    """Basketball-Reference-style abbreviation for a Team enum value string."""
    meta = TEAM_METADATA.get(team)
    return meta[0] if meta else "UNK"


def team_conference(team: str) -> str:
    meta = TEAM_METADATA.get(team)
    return meta[1] if meta else "Unknown"


def team_division(team: str) -> str:
    meta = TEAM_METADATA.get(team)
    return meta[2] if meta else "Unknown"


# Reverse view, keyed by abbreviation -> (full_name, conference, division). The gamelog
# pages and their ``opp_id`` cells identify teams by abbreviation, so this is the join key
# used end-to-end in the demo.
ABBREVIATION_METADATA = {
    abbr: (name, conf, div) for name, (abbr, conf, div) in TEAM_METADATA.items()
}

# The 30 current franchises (Basketball Reference URL/abbreviation codes) — these are the
# gamelog pages we scrape: /teams/{ABBR}/{season_end_year}/gamelog/
CURRENT_TEAM_ABBREVIATIONS = [
    abbr for _name, (abbr, _conf, div) in TEAM_METADATA.items() if div != "Historical"
]


def team_name_from_abbreviation(abbr: str) -> str:
    meta = ABBREVIATION_METADATA.get(abbr)
    return meta[0] if meta else abbr


def conference_from_abbreviation(abbr: str) -> str:
    meta = ABBREVIATION_METADATA.get(abbr)
    return meta[1] if meta else "Unknown"


def division_from_abbreviation(abbr: str) -> str:
    meta = ABBREVIATION_METADATA.get(abbr)
    return meta[2] if meta else "Unknown"


if __name__ == "__main__":
    # Lightweight self-checks — `python nba_helpers.py` should print "ok".
    # eFG%: 38 FGM, 11 3PM, 95 FGA -> (38 + 5.5) / 95 = 0.45789...
    assert abs(effective_field_goal_pct(38, 11, 95) - 0.457894) < 1e-5
    # TOV%: 18 TOV, 95 FGA, 17 FTA -> 18 / (95 + 7.48 + 18) = 18 / 120.48 = 0.14940...
    assert abs(turnover_pct(18, 95, 17) - 0.149402) < 1e-5
    # ORB%: 9 ORB vs opp 35 DRB -> 9 / 44 = 0.204545
    assert abs(offensive_rebound_pct(9, 35) - 0.204545) < 1e-5
    # FT rate: 12 FTM / 95 FGA = 0.126315
    assert abs(free_throw_rate(12, 95) - 0.126316) < 1e-5
    assert effective_field_goal_pct(0, 0, 0) is None  # no divide-by-zero blow-ups
    assert team_abbreviation("BOSTON CELTICS") == "BOS"
    assert team_conference("DENVER NUGGETS") == "West"
    assert team_name_from_abbreviation("BOS") == "BOSTON CELTICS"
    assert conference_from_abbreviation("DEN") == "West"
    assert len(CURRENT_TEAM_ABBREVIATIONS) == 30  # exactly the 30 current franchises
    # Eastern date: 02:30 UTC tip-off is the *previous* Eastern day.
    assert eastern_game_date(datetime(2024, 1, 16, 2, 30, tzinfo=_UTC)) == date(2024, 1, 15)
    print("ok")
