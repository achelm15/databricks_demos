"""Entity registry + silver column maps for the Synergy Baseball demo.

Synergy responses are objects with nested objects, so silver is built with VARIANT-path navigation
(``data:a:b::type``) rather than heavy ``from_json`` schemas. Each entity lists ``(variant_path, alias,
type)`` triples; the 03_silver notebook turns these into a typed ``SELECT``. **To add an entity** for the
handoff: register it in ``ENTITIES`` and drop its column list in ``SILVER_COLUMNS`` (copy/paste the
projection straight from the mlb_pipelines accelerator's ``src/synergy/<entity>/endpoint.yml``).

These two (teams, games) are worked end-to-end as the reference example; the lists are representative
subsets — paste the full projections from the accelerator to go comprehensive.
"""

# name -> how 01_ingest pulls it. kind: "reference" (pull all) | "date_scoped" (minDate/maxDate + season).
ENTITIES = [
    {"name": "teams", "path": "/api/teams/filter", "kind": "reference"},
    {"name": "games", "path": "/api/games/filter", "kind": "date_scoped"},
    # TODO(SA): fan out the rest from the accelerator — players, venues, leagues, events,
    # practice_sessions, umpires, ... (each is /api/<entity>/filter; add its kind + column map).
]

# entity -> [(variant_path_under_`data`, output_alias, spark_type)]
SILVER_COLUMNS = {
    "teams": [
        ("id", "id", "string"),                                  # natural key
        ("externalIdMlbam", "external_id_mlbam", "int"),         # MLBAM crosswalk -> statsapi/people, gold.dim_player
        ("name", "name", "string"),
        ("nameAbbrev", "name_abbrev", "string"),
        ("leagueId", "league_id", "string"),
        ("league:name", "league_name", "string"),
        ("league:nameAbbrev", "league_name_abbrev", "string"),
        ("division:id", "division_id", "string"),
        ("division:name", "division_name", "string"),
        ("conference:id", "conference_id", "string"),
        ("conference:name", "conference_name", "string"),
        ("parentTeamId", "parent_team_id", "string"),
        ("owner:team:id", "owner_team_id", "string"),
        ("datasourceId", "datasource_id", "string"),
        ("dateUpdated", "date_updated", "timestamp"),
    ],
    "games": [
        ("id", "id", "string"),                                  # natural key
        ("season", "season", "int"),
        ("date", "game_date", "timestamp"),
        ("status", "status", "string"),
        ("homeTeam:id", "home_team_id", "string"),
        ("homeTeam:name", "home_team_name", "string"),
        ("awayTeam:id", "away_team_id", "string"),
        ("awayTeam:name", "away_team_name", "string"),
        ("homeTeam:division:id", "home_team_division_id", "string"),
        ("awayTeam:division:id", "away_team_division_id", "string"),
        ("owner:team:id", "owner_team_id", "string"),
        ("datasourceId", "datasource_id", "string"),
        ("dateUpdated", "date_updated", "timestamp"),
        ("gameEventsDateUpdated", "game_events_date_updated", "timestamp"),
    ],
}

# Natural keys (for the silver PK constraint).
PRIMARY_KEYS = {"teams": ["id"], "games": ["id"]}
