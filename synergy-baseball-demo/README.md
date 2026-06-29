# Synergy Baseball — Databricks Solution Accelerator

A **Databricks Solution Accelerator** that ingests [Synergy Sports Baseball](https://synergysports.com/)
data through a Unity Catalog **medallion** (bronze → silver → gold) and exposes it for natural-language
analytics via a **Genie space**. Dual-mode notebooks run from a laptop via **Databricks Connect** *or*
inside a Databricks workspace / Git Folder.

End to end, it:

1. **Ingests** every bulk Synergy data endpoint into a raw Volume, scoping each route the way the API
   actually requires (`01`).
2. **Auto Loads** the raw JSON into bronze `VARIANT` tables (`02`).
3. **Shreds** the VARIANT into typed, conformed silver tables driven by spec-verified column maps (`03`).
4. **Gates** every silver table with **Databricks DQX**, quarantining bad rows so they never reach gold (`04`).
5. **Models** a customer-facing **gold star schema** with RELY PK/FK constraints (`05`).
6. **Annotates** gold and stands up a **Genie space** for natural-language Q&A (`06`).

> Designed to be installed in a customer workspace and pointed at their own Synergy credentials. The
> column projections and API contract are verified against the Synergy OpenAPI spec; field *availability*
> and which endpoints return data depend on the customer's Synergy entitlements (see
> **[Known limitations](#known-limitations--api-notes)**).

---

## What's here

| File | What it does |
|---|---|
| `synergy_client.py` | `SynergyAPI` — OAuth2 client-credentials (or a pre-issued bearer token), auto-paginated `POST /api/<entity>/filter`, `filter_by_ids()` for id-scoped routes, plus `get_by_id()` / `sign_videos()` lookup helpers. |
| `synergy_schemas.py` | `ENTITIES` registry (all 19 bulk endpoints, each with a `scope`) + `SILVER_COLUMNS` `(path, alias, type)` maps verified against the OpenAPI spec. **The extension point.** |
| `00_verify_connection.ipynb` | Spark + UC schemas/Volume + Synergy OAuth probe. **Run first.** |
| `01_ingest_synergy_api.ipynb` | Scope-aware ingest of every entity → raw JSON in the Volume (see [How ingest is scoped](#how-ingest-is-scoped)). |
| `02_bronze_autoloader.ipynb` | Auto Loader JSON → `bronze_<entity>` (`data VARIANT`). |
| `03_silver_transformations.ipynb` | Shred VARIANT → typed `silver_<entity>` for every entity (empty-but-typed shell if a source landed no data). |
| `04_data_quality.ipynb` | **DQX** gate — key-not-null baseline per silver table; failures → `{schema}_quarantine.<entity>`. |
| `05_gold_star_schema.ipynb` | Gold star schema — dims (`dim_team`, `dim_player`, `dim_date`, `dim_venue`, `dim_competition`, `dim_umpire`, `dim_session`) + facts (`fact_game`, `fact_event`, `fact_pitch`, `fact_practice_event`, `fact_practice_workout`, `fact_roster_stint`) with RELY PK/FK constraints. |
| `06_genie_and_dashboard.ipynb` | Annotates gold (table/column `COMMENT`s) and builds a Genie space over the practice star via the SDK. |
| `tests/generate_fake_data.ipynb` | Schema-driven synthetic data for **all** entities → run `02`/`03` **without credentials**. |
| `.env.example` | Copy to `.env`. Creds resolve from `.env` or a `synergy` secret scope. |

**The 19 entities** (every bulk `/filter` endpoint in the spec): `teams`, `games`, `players`,
`players_teamhistory`, `events`, `events_pitch_subset`, `events_defense_subset`, `events_game_state_subset`,
`leagues`, `divisions`, `conferences`, `competitions`, `venues`, `umpires`, `practice_sessions`,
`practice_events`, `practice_training_workout`, `search_players`, `search_teams`. The 12 `GET /{id}` lookups
return the identical schema to their `/filter` item, so they're exposed as client helpers (`get_by_id`),
not tables; `videos/sign` is the `sign_videos()` helper; `search_*` are skipped (redundant with
`players`/`teams`).

## The data flow

```
Synergy API ──01──▶ /Volumes/.../raw_data/<entity>/*.json
                          │
                    02 (Auto Loader, cloudFiles JSON → VARIANT)
                          ▼
              {schema}_bronze.bronze_<entity>        (data VARIANT + _ingestion_timestamp)
                          │
                    03 (data:path::type, dedup to natural key)
                          ▼
              {schema}_silver.silver_<entity>        (typed, conformed)
                          │
                    04 (DQX gate — valid rows stay, failures → {schema}_quarantine.<entity>)
                          ▼
              {schema}_gold.dim_* / fact_*           (star schema, RELY PK/FK)
                          ▼
                    06  Genie space over gold
```

**Why VARIANT, not `from_json`?** Synergy payloads are deeply nested and evolve; landing the whole row as
`data VARIANT` and navigating with `data:home_team:id::string` in silver means new fields never break
ingest — you opt into columns by adding them to `synergy_schemas.SILVER_COLUMNS`.

## How ingest is scoped

**The date range is the only scoping knob.** Dimensions are pulled in full (so fact foreign keys always
resolve); the time-series facts are windowed by `SYNERGY_START_DATE` / `SYNERGY_END_DATE`. Each entity
declares **how it's pulled** via a `scope` field in `ENTITIES`, and `01` is just a dispatcher:

| `scope` | How it's pulled | Entities |
|---|---|---|
| `reference` | `POST /filter`, empty body, **pull all** (dimensions) | `teams`, `players`, `venues`, `umpires`, `leagues`, `divisions`, `conferences`, `competitions` |
| `date` | windowed by `SYNERGY_START_DATE` / `SYNERGY_END_DATE` (`games` also gets a `season` derived from the start-date year) | `games`, `practice_sessions` |
| `session` | by `practiceSessionIds` (derived from the date-windowed `practice_sessions`) | `practice_events`, `practice_training_workout` |
| `team_event` | by `{teamIds: SYNERGY_TEAM_IDS}` + the date window | `events`, `events_*_subset` |
| `team` | one `{teamId}` call per id in `SYNERGY_TEAM_IDS` | `players_teamhistory` |
| `skip` | not ingested | `search_players`, `search_teams` |

Two things to know:
- **`players` is the full ~293k catalog.** The API has no usable activity-date filter for it, so it's pulled
  as a dimension in full. Expect a multi-minute pull and a large `dim_player`.
- **Events scope by `teamIds`, not date alone.** Date-only events are an all-orgs, ~11k-rows/day firehose
  (the API even caps a date-only query to 3 months). Passing `teamIds` (from `SYNERGY_TEAM_IDS`) limits events
  to your teams *and* lifts that cap — so set `SYNERGY_TEAM_IDS` to pull events; **they're skipped when it's
  unset.** `players_teamhistory` is also team-keyed — it *can't* be date-scoped (the API returns 400
  without a `teamId`), so it's pulled from the explicit `SYNERGY_TEAM_IDS` list — leave that blank to skip it
  (its `fact_roster_stint` stays empty). `search_*` are skipped as redundant typeahead duplicates.

## Setup

1. **Install deps** (local): `pip install -r requirements.txt`
2. **Configure** — `cp .env.example .env` and fill in `UC_CATALOG`, `UC_SCHEMA`, and either
   `DATABRICKS_HOST`/`DATABRICKS_TOKEN` (laptop) or run inside a Databricks Git Folder.
3. **Synergy credentials** — locally, put `SYNERGY_CLIENT_ID`/`SYNERGY_CLIENT_SECRET` in `.env`. To run in
   the workspace (or via the pipeline Job), add them to a Databricks **secret scope** instead — see
   [Adding your Synergy credentials to Databricks](#adding-your-synergy-credentials-to-databricks-secret-scope).
4. **Scope** — set `SYNERGY_START_DATE` / `SYNERGY_END_DATE` for the date window, and `SYNERGY_TEAM_IDS`
   for the team-keyed routes (events and `players_teamhistory`).

**Prerequisites:** Unity Catalog enabled, Serverless compute, an existing catalog you can create schemas in
(the notebooks create the `_bronze`/`_silver`/`_gold`/`_quarantine` schemas + a `raw_data` Volume, but assume
the catalog already exists), and a SQL Warehouse (`SQL_WAREHOUSE_ID`) for the Genie space.

## Adding your Synergy credentials to Databricks (secret scope)

When the notebooks run **in the workspace** (including the pipeline Job), they read your Synergy credentials
from a Databricks **secret scope** named `synergy`, keys `client_id` / `client_secret`. (`get_secret()` checks
`.env` first, then this scope — so the same notebook runs locally and in the workspace.) Create it once with
the [Databricks CLI](https://docs.databricks.com/dev-tools/cli/index.html):

```bash
# 1. Create the scope (Databricks-backed). Use -p <profile> to target the right workspace.
databricks secrets create-scope synergy -p <your-profile>

# 2. Add each secret. Run WITHOUT --string-value so the CLI opens your $EDITOR and the value never lands
#    in shell history — paste the value, save, close.
databricks secrets put-secret synergy client_id      -p <your-profile>
databricks secrets put-secret synergy client_secret  -p <your-profile>

# 3. Verify — lists key names + timestamps only, never the values.
databricks secrets list-secrets synergy -p <your-profile>
```

- **Names must match exactly:** scope `synergy`, keys `client_id` and `client_secret` — that's what the
  notebooks request, so a differently-named scope won't be found.
- **Where to get the values:** your Synergy account rep (OAuth2 client credentials).
- **Job access:** the Job runs as the deploying user by default, who is `MANAGE` on a scope they created, so
  it can read the secrets. If you run the Job as a **service principal**, grant it read:
  `databricks secrets put-acl synergy <sp-application-id> READ`.
- **Never** commit the credentials or paste them into a notebook — the secret scope (workspace) and `.env`
  (local, gitignored) are the only two places they should live.

## Run it

```
00_verify_connection      →  proves Spark + UC + Synergy auth all work
01_ingest_synergy_api     →  scope-aware pull of every entity into the Volume
02_bronze_autoloader      →  Auto Loads them to bronze_<entity>
03_silver_transformations →  builds typed silver_<entity> for all entities
04_data_quality           →  DQX gate: validates silver, quarantines failures
05_gold_star_schema       →  builds the gold star schema (dims + facts, RELY constraints)
06_genie_and_dashboard    →  annotates gold + builds the Genie space
```

### No Synergy credentials yet?

Run **`tests/generate_fake_data.ipynb`** instead of `01`. It writes schema-driven synthetic data for **all**
entities into the Volume, then `02` → `06` run end-to-end offline, so you can exercise the pipeline before
live credentials are provisioned.

## Cross-source conformance — the key idea

`silver_teams.external_id_mlbam` (and `silver_players.external_id_mlbam`) is the **MLBAM id** — the standard
cross-source join key in baseball data. Carried through to `dim_team.mlbam_team_id` / `dim_player.mlbam_player_id`,
it means this Synergy data lines up with any other MLBAM-keyed source the customer has, on the same ids.

## Customizing for your data

- **Credentials** → your Synergy `client_id`/`client_secret` (secret scope `synergy`).
- **Scope** → `SYNERGY_START_DATE` / `SYNERGY_END_DATE` (date window) + `SYNERGY_TEAM_IDS` (teams you own).
- **Columns** → add/trim `(path, alias, type)` triples in `synergy_schemas.SILVER_COLUMNS`. The wide
  `events` / `practice_events` tables expose every scalar leaf in the spec; the `events_*_subset` tables are
  leaner ready-to-use views.
- **Data quality** → extend the DQX checks in `04` beyond the key-not-null baseline (date ranges, enum
  membership, referential checks against your dims).
- **Genie** → curate sample questions, instructions, and certified example SQL in `06`.

## Known limitations & API notes

- **Transient API errors.** The Synergy API returns intermittent `5xx` (with a `CorrelationID`) on
  individual routes. Each notebook tolerates per-entity failures (it logs and continues), but a route that
  errors will land 0 rows for that run — re-run, or report the `CorrelationID` to Synergy. (Auth failures, by
  contrast, are `401` — a `500` means your request was accepted and failed server-side.)
- **Field availability varies by org/datasource.** A field present in the spec may be unpopulated for a given
  customer's data — e.g. practice `contact.exitSpeedMph` (exit velocity) can be absent even when launch
  angle, spin, and distance are present. Empty columns are usually a source/entitlement gap, not a pipeline
  bug; verify against the raw `/filter` response.
- **Two scoping axes: date and team.** `SYNERGY_START_DATE`/`END_DATE` window `games` and `practice_sessions`
  (which scopes `practice_events`); `SYNERGY_TEAM_IDS` scopes `events` and `players_teamhistory`. Dimensions
  (incl. all ~293k `players`) are pulled in full. If a fact table is empty, widen the window or set the team ids.
- **Events need `SYNERGY_TEAM_IDS`.** Date-only events are an all-orgs ~11k-rows/day firehose (and the API
  caps a date-only query to 3 months); passing `teamIds` scopes them to your teams and lifts the cap. So set
  `SYNERGY_TEAM_IDS` to your club/affiliate ids to pull events — otherwise the event routes are skipped.
- **Full refresh.** `silver`/`gold` use `CREATE OR REPLACE` (Spark Connect can't `MERGE`). Bronze is
  incremental via Auto Loader; for incremental silver/gold on large volumes, switch those writes to `MERGE`
  when running inside a Databricks cluster.

## Notes & gotchas (learned running this)

- **Auth from a laptop:** Databricks Connect picks up auth from the SDK config chain. The cleanest path is a
  CLI OAuth profile (`databricks auth login`, then `DATABRICKS_CONFIG_PROFILE=<profile>`). A stale PAT in
  `.env` will override the profile and 403 — leave `DATABRICKS_TOKEN` blank if you use a profile. If multiple
  profiles match your host, set `DATABRICKS_CONFIG_PROFILE` to disambiguate.
- **Writing to the Volume over Connect:** the notebooks land JSON with the **SDK Files API**
  (`w.files.upload`, with a `BytesIO` seekable stream), *not* local `open()` — a laptop has no `/Volumes`
  FUSE mount.
- **Bronze needs `cloudFiles.inferColumnTypes`:** without it Auto Loader reads nested JSON objects as
  *strings* and every nested silver column comes out NULL. It's set in `02`.
- **Synergy date filters want `MM/DD/YYYY`,** not ISO — `01` converts automatically; passing ISO is silently
  ignored by the API.
- **Silver casts via `data:path::type`.** If a messier live entity has junk values that hard-fail a cast,
  switch that column to `try_cast(data:path::string AS type)` (nulls bad values instead of erroring).

---

> **Never commit credentials.** `.env` is gitignored; real `client_id` / `client_secret` live only in
> `.env` (local) or the `synergy` secret scope (workspace).
