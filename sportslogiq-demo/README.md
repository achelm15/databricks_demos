# SportLogiq NHL — Hockey Analytics Accelerator

A medallion-architecture accelerator that lands the **SportLogiq Hockey REST API** into Unity Catalog as governed Bronze → Silver → Gold tables, then builds an AI/BI dashboard and Genie space on top — all from local Jupyter notebooks via **Databricks Connect (serverless)** *or* directly inside a **Databricks workspace Git Folder**.

Built for NHL clubs (and other SportLogiq subscribers) that already have credentials and want a turn-key pattern for ingesting their game/event/metric feed onto Databricks.

## Overview

- **Comprehensive API coverage** — ~25 of the SportLogiq routes are pulled, from reference data (teams, venues, players, competitions, metric topics) through per-game payloads (rosters, compiled events, full events, shifts, TOI, per-topic metrics) to season-aggregate competition metrics across the player / team / goalie / opposingteam scopes, plus xrefs and player history sampling
- **Backfill flexibility** — one ingest notebook, four modes: `daily`, `season`, `team`, `date_window`. Files already in the Volume are skipped, so re-runs are safe and resumable
- **VARIANT bronze** — raw JSON lands as `data VARIANT`, navigable with `data:field::type`. PySpark schemas in `sportlogiq_schemas.py` drive array-shape extraction in silver
- **Full medallion** — typed silver, MD5 surrogate keys, RELY PK/FK, liquid clustering tuned to query shape, INSERT OVERWRITE for restart-safe full refresh
- **Star-schema gold** — five dimensions, four facts, three pre-aggregated views ready for AI/BI and Genie
- **Dual-mode** — same notebooks run from a laptop *and* in a Databricks Git Folder. Secrets resolve from `.env` first, then fall back to a workspace secret scope

> **Databricks Connect note.** Silver and Gold use `INSERT OVERWRITE` instead of `MERGE` — `MERGE` is not supported through Spark Connect. If you run the notebooks inside a Databricks workspace cluster, you can swap `INSERT OVERWRITE` for `MERGE` to get incremental loads; the schema remains identical.

## Architecture

```
┌────────────────────────────────────────────────────────────────────────────┐
│  SportLogiq Hockey REST API  (api.sportlogiq.com)                          │
│  ~25 routes — reference, per-game, per-season metrics, xrefs               │
└──────────────────────────────────┬─────────────────────────────────────────┘
                                   │
                                   ▼
┌────────────────────────────────────────────────────────────────────────────┐
│  01_ingest_sportlogiq_api                                                   │
│  Modes: daily | season | team | date_window  →  UC Volume raw_data/        │
│         reference/  games/{id}/  season_metrics/  xrefs/  player_history/  │
└──────────────────────────────────┬─────────────────────────────────────────┘
                                   │
                                   ▼
┌────────────────────────────────────────────────────────────────────────────┐
│  BRONZE (02_bronze_autoloader)                                              │
│  Auto Loader (availableNow) → 16 VARIANT-typed Delta tables                 │
└──────────────────────────────────┬─────────────────────────────────────────┘
                                   │
                                   ▼
┌────────────────────────────────────────────────────────────────────────────┐
│  SILVER (03_silver_transformations)                                         │
│  data:field::type extraction + from_json + LATERAL VIEW EXPLODE             │
│  MD5 SKs, RELY PK/FK, liquid clustering, INSERT OVERWRITE                   │
│  competitions / teams / team_records / venues / players / metric_topics /   │
│  games / game_rosters / compiled_events / full_events / shift_events /      │
│  player_toi / player_game_metrics / season_metrics                          │
└──────────────────────────────────┬─────────────────────────────────────────┘
                                   │
                                   ▼
┌────────────────────────────────────────────────────────────────────────────┐
│  GOLD (04_gold_star_schema)                                                 │
│  dim_team / dim_player / dim_venue / dim_game / dim_date                    │
│  fact_game_events / fact_player_shifts                                      │
│  fact_player_game_metrics / fact_player_season_metrics                      │
│  v_team_standings / v_player_season_leaders / v_shot_map                    │
└──────────────────────────────────┬─────────────────────────────────────────┘
                                   │
                                   ▼
┌────────────────────────────────────────────────────────────────────────────┐
│  GOVERNANCE (05) → DASHBOARD (06) → GENIE (07)                              │
│  Comments + tags + lineage  →  Lakeview AI/BI  →  hockey-aware Genie space  │
└────────────────────────────────────────────────────────────────────────────┘
```

## Notebook reference

| # | Notebook | Purpose |
|---|----------|---------|
| 00 | `00_verify_connection.ipynb` | Verify Spark + UC + SportLogiq login. Creates schemas + Volume |
| 01 | `01_ingest_sportlogiq_api.ipynb` | Ingest reference + per-game + season + xrefs into UC Volume. Modes: `daily / season / team / date_window` |
| 02 | `02_bronze_autoloader.ipynb` | Auto Loader → VARIANT bronze tables (16 of them) |
| 03 | `03_silver_transformations.ipynb` | Typed silver, MD5 SKs, RELY PK/FK, liquid clustering |
| 04 | `04_gold_star_schema.ipynb` | Star schema + analytical views |
| 05 | `05_catalog_enrichment.ipynb` | Comments, tags, lineage check |
| 06 | `06_create_dashboard.ipynb` | Lakeview dashboard via API (idempotent: updates in place if it exists) |
| 07 | `07_create_genie_space.ipynb` | Genie space with hockey terminology (Corsi, Fenwick, TOI, zones, strength state) |

Run them in order. 02 depends on 01, 03 on 02, etc.

## Sanity-check without API credentials

Don't have SportLogiq creds yet? `tests/generate_fake_data.ipynb` lays down a
small synthetic corpus in the same UC Volume paths the real ingest writes to,
so notebooks 02-07 run end-to-end against fake data. Useful for proving the
bronze→gold→dashboard→Genie code is structurally sound before creds arrive.
See `tests/README.md` for the workflow (skip 00 + 01, run the test notebook,
then 02-07 normally).

## Running mode 1 — Local (Databricks Connect)

The default. Notebooks run on your laptop, compute happens on a Databricks Serverless warehouse you point them at.

### 1. Clone + venv
```bash
cd sportslogiq-demo
python -m venv .venv
source .venv/bin/activate            # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

### 2. Configure `.env`
```bash
cp .env.example .env
# Edit .env — see Configuration below
```

### 3. Run
```bash
jupyter lab    # or: jupyter notebook
```

Open notebooks in order, `00 → 07`.

## Running mode 2 — Databricks workspace (Git Folder)

The same `.ipynb` files run inside Databricks, attached to a workspace cluster or Serverless. Three things change:

1. **No Databricks Connect import.** Each notebook starts with:
   ```python
   try:
       spark
   except NameError:
       from databricks.connect import DatabricksSession
       spark = DatabricksSession.builder.serverless().getOrCreate()
   ```
   Inside Databricks, `spark` already exists, so the `import` line is skipped automatically. **Nothing to edit.**
2. **Authentication is implicit.** Drop `DATABRICKS_HOST` and `DATABRICKS_TOKEN` from `.env` — the workspace provides them. `WorkspaceClient()` picks up the implicit credentials.
3. **SportLogiq credentials.** Two options:
   - **(Recommended) Workspace secret scope.** Create a scope named `sportlogiq` and add `username` + `password` keys:
     ```bash
     databricks secrets create-scope sportlogiq
     databricks secrets put-secret sportlogiq username --string-value '...'
     databricks secrets put-secret sportlogiq password --string-value '...'
     ```
     The `get_secret()` helper in every notebook tries `os.getenv` first, then falls back to `dbutils.secrets.get(scope="sportlogiq", key=...)`, so this works with no code changes.
   - **Cluster environment variables.** Compute → your cluster → Edit → Advanced → Environment variables. Add `SPORTLOGIQ_USERNAME=...`, `SPORTLOGIQ_PASSWORD=...`, `UC_CATALOG=...`, `UC_SCHEMA=...`, `SQL_WAREHOUSE_ID=...`. Restart the cluster. `os.getenv` will pick them up.

### Steps to import as a Git Folder
1. In Databricks, **Workspace → Repos → Add Repo** (or **Git Folders → Add**).
2. Point at this repo. The folder appears with all the `.ipynb` files visible to the workspace.
3. Set up either secrets or env vars as above.
4. Set `UC_CATALOG`, `UC_SCHEMA`, `SQL_WAREHOUSE_ID` (and the SportLogiq creds if not in secrets) at the cluster level.
5. Open `00_verify_connection.ipynb` and Run All. Then 01, 02, ...

### Where you can do *more* in workspace mode

A few things are easier in-workspace; feel free to swap them in once you're running there:

| Local | In-workspace upgrade |
|-------|---------------------|
| `INSERT OVERWRITE` for full refresh | Swap to `MERGE INTO` for incremental updates — works because Spark Connect's MERGE limitation doesn't apply on workspace clusters |
| Auto Loader `availableNow=True` (one-shot) | Switch to a continuous trigger and schedule via Databricks Jobs |
| Single-notebook execution | Wrap notebooks 01–07 as a Databricks Job DAG; 01 daily, 02–07 chained on success |

## Configuration (`.env`)

| Variable | Required | Notes |
|----------|----------|-------|
| `DATABRICKS_HOST` | Local only | Workspace URL |
| `DATABRICKS_TOKEN` | Local only | PAT or OAuth token |
| `DATABRICKS_CLUSTER_ID` | No | Leave blank for Serverless (recommended) |
| `UC_CATALOG` | Yes | Existing catalog you can `CREATE SCHEMA` in |
| `UC_SCHEMA` | Yes | Base name → creates `{schema}_bronze`, `_silver`, `_gold` |
| `SPORTLOGIQ_USERNAME` | Yes | SportLogiq Hockey API username |
| `SPORTLOGIQ_PASSWORD` | Yes | SportLogiq Hockey API password |
| `NHL_SEASON` | Yes | SportLogiq season format `YYYYYYYY` (e.g. `20232024`) |
| `NHL_TEAM_ID` | No | If `INGEST_MODE=team`, scopes ingest to one club (~82 games) |
| `NHL_START_DATE`, `NHL_END_DATE` | No | If `INGEST_MODE=date_window`, both inclusive `YYYY-MM-DD` |
| `NHL_COMPETITION_ID` | No | Defaults to `1` (NHL). Override for AHL, etc. |
| `INGEST_MODE` | No | `daily` (default), `season`, `team`, or `date_window` |
| `INGEST_WORKERS` | No | Per-game fan-out concurrency (default `6`) |
| `PLAYER_HISTORY_LIMIT` | No | Cap on the player-history sample (default `50`) |
| `SQL_WAREHOUSE_ID` | Yes for 06, 07 | SQL Warehouse used by the dashboard + Genie space |
| `DOMAIN`, `DATA_OWNER` | No | Override the default tag values applied in 05 |

## SportLogiq route coverage

| Route (client method) | Where it lands |
|-----------------------|----------------|
| `get_competitions`, `get_competition` | `bronze_competitions` → `silver_competitions` |
| `get_teams` | `bronze_teams` → `silver_teams` → `dim_team` |
| `get_team_records` | `bronze_team_records` → `silver_team_records` → `v_team_standings` |
| `get_venues` | `bronze_venues` → `silver_venues` → `dim_venue` |
| `get_players` | `bronze_players` → `silver_players` → `dim_player` |
| `get_metric_topics(scope)` × 4 scopes | `bronze_metric_topics` → `silver_metric_topics` (catalog of metric definitions) |
| `get_game` | `bronze_game` → `silver_games` → `dim_game` |
| `get_game_roster` | `bronze_game_rosters` → `silver_game_rosters` |
| `get_game_compiled_events` | `bronze_compiled_events` → `silver_compiled_events` → `fact_game_events` |
| `get_game_full_events` | `bronze_full_events` → `silver_full_events` |
| `get_player_shift_events` | `bronze_shift_events` → `silver_shift_events` → `fact_player_shifts` |
| `get_game_player_toi` | `bronze_player_toi` → `silver_player_toi` |
| `get_game_metrics(topic)` × N topics | `bronze_game_metrics` → `silver_player_game_metrics` → `fact_player_game_metrics` |
| `get_competition_metrics(scope, topic)` × 4 scopes × N topics | `bronze_season_metrics` → `silver_season_metrics` → `fact_player_season_metrics` |
| `get_xrefnames`, `get_external_*_references` × 4 entities | `bronze_xrefs` (kept as VARIANT — surface as a join helper in customer-specific layers) |
| `get_player_team_history` *(sampled)* | `bronze_player_history` |

Routes intentionally not pulled in the accelerator (you can add them by extending the `routes` list in notebook 01):

- `post_video_times` — push, not pull. Coaching-video integration; out of scope for an analytics accelerator.
- `get_team_metrics(team_id, topic_id)` and `get_player_metrics(player_id, topic_id)` — overlap with `get_competition_metrics` at the season grain. Add per-team / per-player calls if you need historical splits the season aggregates don't expose.
- `get_game_leaders` — pre-summarised leaderboards. The same answer comes from `fact_player_game_metrics` once you have it; Genie can compute it on the fly.

## Key implementation details

- **VARIANT bronze.** Every bronze table has `data VARIANT, _ingestion_timestamp, _source_file, _rescued`. `_rescued` is the schema-drift safety net — if SportLogiq adds a field, it lands in rescue, never on the floor.
- **Silver array extraction.** Some payloads (compiled events, metric groupings, embedded teams/venues/players arrays) are nested shapes that VARIANT path syntax can't reach in a single expression. Silver uses `from_json(data:field::string, '<schema>')` plus `LATERAL VIEW EXPLODE` to flatten them, with the schema literal inlined per cell so each block is self-contained. `sportlogiq_schemas.py` is **reference-only documentation** — it ships PySpark `StructType` definitions for every route response, useful when authoring new silver blocks, but it is not imported at runtime.
- **MD5 surrogate keys.** Restart-safe, deterministic. `event_sk = MD5(game_id || event_id || event_sequence_id)`, etc.
- **RELY PK/FK constraints.** Informational — no runtime cost — but they unlock the Catalog Explorer ERD, drive AI/BI auto-join inference, and improve Genie's joins.
- **Liquid clustering.** Tuned to predicate shape: `silver_games CLUSTER BY (game_date, home_team_id)`, `silver_compiled_events CLUSTER BY (game_id, period)`, `fact_game_events CLUSTER BY (season, game_date, team_id)`, etc.
- **Idempotency.** Notebook 01 calls `w.files.get_metadata(path)` before each upload — files already in the Volume are skipped. Auto Loader's checkpoint handles bronze idempotency. Silver/Gold use `INSERT OVERWRITE`.

## Troubleshooting

| Issue | Fix |
|-------|-----|
| `SportLogiqAPIError: login failed (401)` | Wrong creds. Validate by hitting `https://api.sportlogiq.com/v1/hockey/login` with curl. |
| `INGEST_MODE=team requires NHL_TEAM_ID` | Add `NHL_TEAM_ID` to `.env`. Pull team IDs from `bronze_teams` after a first reference run. |
| Bronze rows = 0 for an entity | The matching glob in 02's `ENTITIES` list found no files. Check `01_ingest` log; the entity may not have been pulled in your selected mode. |
| `UnsupportedOperationException: MERGE` | You hit a stray `MERGE`. Silver/gold should be `INSERT OVERWRITE` — confirm no edits drifted. |
| `system.access.column_lineage` empty in 05 | Lineage requires gold tables to have been *queried* once after creation. Open them in Catalog Explorer or run a SELECT and re-run 05. |
| Duplicate Lakeview / Genie space on re-run | 06 and 07 both look up the existing object and update in place — confirm `parent_path` matches `/Workspace/Users/{your_email}`. |
| Databricks Connect version mismatch | Align `databricks-connect` in `requirements.txt` with the workspace's runtime (major.minor must match). |

## Cleanup

```python
# From any notebook after preamble + config:
for schema in [GOLD_SCHEMA, SILVER_SCHEMA, BRONZE_SCHEMA]:
    spark.sql(f"DROP SCHEMA IF EXISTS {UC_CATALOG}.{schema} CASCADE")
```

That drops all tables and the Volume. Drop the Lakeview dashboard and Genie space via the Databricks UI when you're done with the engagement.

## What's *not* included (extension points)

- **DLT / Lakeflow Declarative Pipelines.** The notebooks are intentionally imperative. If you'd rather express bronze→silver as a DLT pipeline, the silver SQL is already pure-SQL `INSERT OVERWRITE` and can be lifted into `@dlt.table` definitions.
- **Genie certified questions / sample questions.** Easy to add via `/api/2.0/genie/spaces/{id}/questions` — left out so the demo is non-clobbering for anyone editing the Genie space by hand.
- **Player birth_city / birth_country PII tagging.** The current `get_players` payload doesn't include birthdate (only `get_player(id)` does). If you extend 01 to call `get_player(id)` per player, add the `pii` column tag in 05 to that field.
- **`xrefs` silver tables.** Bronze `bronze_xrefs` keeps the raw payload as VARIANT. Customers usually need a custom join shape against their own systems-of-record, so we leave that to the implementation team.
