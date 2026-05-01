"""SportLogiq Hockey REST API client.

Cleaned-up version of the original `sportlogiq_nhl_api.py`:
- Drops requests_oauthlib import (never used; SportLogiq uses session cookies)
- Raises on login failure instead of just printing
- Uses timezone-aware UTC datetimes
- Removes orphan/dead code in score formatting
"""
from __future__ import annotations

import datetime as _dt
from typing import Any

import requests


class SportLogiqAPIError(RuntimeError):
    pass


class SportLogiqAPI:
    """High-level client for the SportLogiq Hockey REST API.

    Auth is session-cookie based — POST /login once, the session carries
    the cookie on every subsequent request.
    """

    BASE_URL = "https://api.sportlogiq.com/v1/hockey/"

    def __init__(self, username: str, password: str, *, timeout: int = 60):
        self.username = username
        self.password = password
        self.timeout = timeout
        self.session = requests.Session()
        self.login()

    # ------------------------------------------------------------------ auth
    def login(self) -> None:
        url = self.BASE_URL + "login"
        resp = self.session.post(
            url,
            json={"username": self.username, "password": self.password},
            timeout=self.timeout,
        )
        if resp.status_code != 201:
            raise SportLogiqAPIError(
                f"SportLogiq login failed ({resp.status_code}): {resp.text[:200]}"
            )

    # ----------------------------------------------------------------- core
    def request(self, method: str, path: str, **kwargs: Any) -> requests.Response:
        url = self.BASE_URL + path
        kwargs.setdefault("timeout", self.timeout)
        return self.session.request(method, url, **kwargs)

    # --------------------------------------------------------------- helpers
    @staticmethod
    def utcnow_iso() -> str:
        """Timezone-aware UTC timestamp formatted for SportLogiq filters."""
        now = _dt.datetime.now(_dt.timezone.utc)
        return now.strftime("%Y-%m-%dT%H:%M:%S.") + f"{now.microsecond // 1000:03d}Z"

    @staticmethod
    def format_game_score(game: dict) -> dict:
        """Flatten the score dict (keyed by team_id) into home/away keys."""
        away_team_id = str(game["away_team_id"])
        home_team_id = str(game["home_team_id"])
        score = game.get("score") or {}
        game["score"] = {
            "away_team_score": score.get(away_team_id),
            "home_team_score": score.get(home_team_id),
        }
        return game

    # ============================ Games ============================
    def get_games(self, **params: Any) -> requests.Response:
        return self.request("GET", "games", params=params)

    def get_game(self, game_id: str) -> requests.Response:
        return self.request("GET", f"games/{game_id}")

    def get_games_by_process_time(self, last_process_time: str) -> dict:
        """List games with metric processing more recent than the given UTC ISO timestamp."""
        response = self.get_games(last_metrics_full_process_time_from=last_process_time).json()
        for game in response.get("games", []):
            self.format_game_score(game)
        return response

    def get_game_ids_by_process_time(self, last_process_time: str) -> list[str]:
        response = self.get_games(last_metrics_full_process_time_from=last_process_time).json()
        return [g["id"] for g in response.get("games", [])]

    def get_games_by_season(self, season: str) -> dict:
        response = self.get_games(season=season).json()
        for game in response.get("games", []):
            self.format_game_score(game)
        return response

    def get_games_by_date(self, season: str, date: str | None = None) -> list[dict]:
        date = date or _dt.date.today().isoformat()
        response = self.get_games(season=season).json()
        games = [g for g in response.get("games", []) if g.get("date") == date]
        for game in games:
            self.format_game_score(game)
        return games

    # ============================ Game detail ============================
    def get_game_roster(self, game_id: str) -> requests.Response:
        return self.request("GET", f"games/{game_id}/roster")

    def get_game_leaders(self, game_id: str, metric: str, **params: Any) -> requests.Response:
        params["metric"] = metric
        return self.request("GET", f"games/{game_id}/leaders", params=params)

    def get_player_shift_events(self, game_id: str) -> requests.Response:
        return self.request("GET", f"games/{game_id}/events/shifts")

    def get_game_full_events(self, game_id: str) -> requests.Response:
        return self.request("GET", f"games/{game_id}/events/full")

    def get_game_compiled_events(self, game_id: str) -> requests.Response:
        return self.request("GET", f"games/{game_id}/events/compiled")

    def get_game_metrics(self, game_id: str, topic_id: str, **params: Any) -> requests.Response:
        return self.request("GET", f"games/{game_id}/metrics/{topic_id}", params=params)

    def get_game_player_toi(self, game_id: str) -> requests.Response:
        return self.request("GET", f"games/{game_id}/playerTOI")

    # ============================ Teams ============================
    def get_teams(self, **params: Any) -> requests.Response:
        return self.request("GET", "teams", params=params)

    def get_team(self, team_id: str) -> requests.Response:
        return self.request("GET", f"teams/{team_id}")

    def get_team_metrics(self, team_id: str, topic_id: str, **params: Any) -> requests.Response:
        return self.request("GET", f"teams/{team_id}/metrics/{topic_id}", params=params)

    def get_team_records(self, **params: Any) -> requests.Response:
        return self.request("GET", "teams/records", params=params)

    def get_team_record(self, team_id: str, **params: Any) -> requests.Response:
        return self.request("GET", f"teams/{team_id}/record", params=params)

    # ============================ Players ============================
    def get_players(self, **params: Any) -> requests.Response:
        return self.request("GET", "players", params=params)

    def get_player(self, player_id: str) -> requests.Response:
        return self.request("GET", f"players/{player_id}")

    def get_player_metrics(self, player_id: str, topic_id: str, **params: Any) -> requests.Response:
        return self.request("GET", f"players/{player_id}/metrics/{topic_id}", params=params)

    def get_player_team_history(self, player_id: str) -> requests.Response:
        return self.request("GET", f"players/{player_id}/history")

    def get_players_by_team(self, team_id: str, season: str) -> list[dict]:
        response = self.get_players(season=season).json()
        return [p for p in response.get("players", []) if p.get("current_team_id") == team_id]

    # ============================ Competitions / metrics ============================
    def get_competitions(self, **params: Any) -> requests.Response:
        return self.request("GET", "competitions", params=params)

    def get_competition(self, competition_id: str) -> requests.Response:
        return self.request("GET", f"competitions/{competition_id}")

    def get_competition_metrics(
        self, competition_id: str, scope: str, topic_id: str, **params: Any
    ) -> requests.Response:
        path = f"competitions/{competition_id}/metrics/{topic_id}?scope={scope}"
        return self.request("GET", path, params=params)

    def get_metric_topics(self, scope: str, **params: Any) -> requests.Response:
        return self.request("GET", f"metrictopics/{scope}", params=params)

    def get_metrics_by_topic(self, scope: str, topic_id: str, **params: Any) -> requests.Response:
        return self.request("GET", f"metrictopics/{scope}/{topic_id}", params=params)

    # ============================ Venues ============================
    def get_venues(self, **params: Any) -> requests.Response:
        return self.request("GET", "venues", params=params)

    def get_venue_info(self, venue_id: str, **params: Any) -> requests.Response:
        return self.request("GET", f"venues/{venue_id}", params=params)

    # ============================ External references ============================
    def get_xrefnames(self) -> requests.Response:
        return self.request("GET", "xrefnames")

    def get_external_game_references(self, xrefname: str) -> requests.Response:
        return self.request("GET", f"references/{xrefname}/games")

    def get_external_player_references(self, xrefname: str) -> requests.Response:
        return self.request("GET", f"references/{xrefname}/players")

    def get_external_team_references(self, xrefname: str) -> requests.Response:
        return self.request("GET", f"references/{xrefname}/teams")

    def get_external_venue_references(self, xrefname: str) -> requests.Response:
        return self.request("GET", f"references/{xrefname}/venues")

    def get_external_game_events_references(self, xrefname: str, game_id: str) -> requests.Response:
        return self.request("GET", f"references/{xrefname}/games/{game_id}/events")

    # ============================ Video times (POST) ============================
    def post_video_times(self, times: list[dict]) -> requests.Response:
        return self.request("POST", "videos/videotimes", json=times)

    def post_single_video_time(
        self,
        game_id: str,
        period: int,
        period_time_sec: int | None = None,
        period_time_formatted: str | None = None,
    ) -> requests.Response:
        entry: dict[str, Any] = {"game_id": game_id, "period": period}
        if period_time_sec is not None:
            entry["period_time_sec"] = period_time_sec
        elif period_time_formatted is not None:
            entry["period_time_formatted"] = period_time_formatted
        return self.post_video_times([entry])
