# Synergy Baseball — Databricks Medallion Demo (Starter)

A **follow-along, notebook-style** demo that ingests [Synergy Sports Baseball](https://synergysports.com/)
data into a Databricks medallion (bronze → silver → gold) on Unity Catalog. Dual-mode notebooks (run from a
laptop via Databricks Connect *or* inside a Databricks Git Folder), Auto Loader bronze, VARIANT-shredded
silver.

> **This is a STARTER for handoff.** It ingests **every bulk data endpoint in the Synergy OpenAPI spec**
> (19 entities) end-to-end through Silver, with projections verified against the spec. Gold and the
> Genie/dashboard layer are scaffolded as `🟡 TODO` stubs for the receiving SA to finish for the customer.
> See **[For the SA finishing this](#for-the-sa-finishing-this)** below.

---

## What's here

| File | Status | What it does |
|---|---|---|
| `synergy_client.py` | ✅ | `SynergyAPI` — OAuth2 client-credentials + auto-paginated `POST /api/<entity>/filter`, plus `get_by_id()` / `sign_videos()` lookup helpers. |
| `synergy_schemas.py` | ✅ | `ENTITIES` registry (all 19) + `SILVER_COLUMNS` `(path, alias, type)` maps, verified against the OpenAPI spec. The extension point. |
| `00_verify_connection.ipynb` | ✅ | Spark + UC schemas/Volume + Synergy OAuth probe. **Run first.** |
| `01_ingest_synergy_api.ipynb` | ✅ | Loop every entity in `ENTITIES` → land JSON in the Volume (reference = pull all, date_scoped = windowed). |
| `02_bronze_autoloader.ipynb` | ✅ | Auto Loader JSON → `bronze_<entity>` (`data VARIANT`) for every entity. |
| `03_silver_transformations.ipynb` | ✅ | Shred VARIANT → typed `silver_<entity>` for every entity. |
| `04_data_quality.ipynb` | ✅ | **DQX** gate — validates every silver table (key-not-null baseline), quarantines failures so bad data never reaches gold. |
| `05_gold_star_schema.ipynb` | 🟡 TODO | `dim_team` worked as a template; dims/facts for the SA to finish. |
| `06_genie_and_dashboard.ipynb` | 🟡 TODO | Plan for the AI/BI dashboard + Genie space over gold. |
| `tests/generate_fake_data.ipynb` | ✅ | Schema-driven synthetic data for **all** entities → run 02/03 **without credentials**. |
| `.env.example` | ✅ | Copy to `.env`. Creds resolve from `.env` or a `synergy` secret scope. |

**The 19 entities** (every bulk `/filter` endpoint in the spec): `teams`, `games`, `players`,
`players_teamhistory`, `events`, `events_pitch_subset`, `events_defense_subset`, `events_game_state_subset`,
`leagues`, `divisions`, `conferences`, `competitions`, `venues`, `umpires`, `practice_sessions`,
`practice_events`, `practice_training_workout`, `search_players`, `search_teams`. The other spec paths
carry no new data: the 12 `GET /{id}` lookups (identical schema to the `/filter` item) + `videos/sign` are
exposed as **client helpers** (`get_by_id` / `sign_videos`), not tables; `*/filter-no-count` is a redundant
dup of the counting `/filter` and is skipped.

> **Verified:** the whole medallion has been run end-to-end via Databricks Connect on synthetic data —
> all 19 bronze + 19 typed silver tables build with populated nested fields (e.g. `events` 272 cols,
> `games` 40), zero errors. Every column path is verified against the Synergy OpenAPI spec.

## The data flow

```
Synergy API ──01──▶ /Volumes/.../raw_data/<entity>/*.json      (all 19 entities)
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
                    05 🟡 (dim_team/dim_player/fact_game ...)
                          ▼
              {schema}_gold.*  ──▶ 06 🟡 Genie space + dashboard
```

**Why VARIANT, not `from_json`?** Synergy payloads are deeply nested and evolve; landing the whole row as
`data VARIANT` and navigating with `data:home_team:id::string` in silver means new fields never break
ingest — you opt into columns by adding them to `synergy_schemas.SILVER_COLUMNS`.

**Lookup helpers (not ingestion).** The spec's 12 `GET /api/<entity>/{id}` endpoints return the *identical
schema* to their `/filter` list item, so they add no data to the medallion. The client exposes them as
spot-check / enrichment helpers instead: `api.get_by_id("teams", "T0001")` and `api.sign_videos([...])`
(for `POST /api/videos/sign`).

## Setup

1. **Install deps** (local): `pip install -r requirements.txt`
2. **Configure** — `cp .env.example .env` and fill in `UC_CATALOG`, `UC_SCHEMA`, and either
   `DATABRICKS_HOST`/`DATABRICKS_TOKEN` (laptop) or run inside a Databricks Git Folder.
3. **Synergy credentials** — set `SYNERGY_CLIENT_ID`/`SYNERGY_CLIENT_SECRET` in `.env`, **or** (preferred
   in a workspace) create a secret scope:
   ```bash
   databricks secrets create-scope synergy
   databricks secrets put-secret synergy client_id
   databricks secrets put-secret synergy client_secret
   ```
   The notebooks' `get_secret()` reads `.env` first, then the scope — so the same notebook runs both places.

## Run it

```
00_verify_connection      →  proves Spark + UC + Synergy auth all work
01_ingest_synergy_api     →  pulls every entity into the Volume
02_bronze_autoloader      →  Auto Loads them to bronze_<entity>
03_silver_transformations →  builds typed silver_<entity> for all 19 entities
04_data_quality           →  DQX gate: validates silver, quarantines failures
05_gold_star_schema       →  🟡 star schema (SA finishes)
06_genie_and_dashboard    →  🟡 Genie + dashboard (SA finishes)
```

### No Synergy credentials yet?

Run **`tests/generate_fake_data.ipynb`** instead of `01`. It writes schema-driven synthetic data for **all
19 entities** into the Volume, then `02` → `03` work end-to-end offline. Perfect for kicking the tires
before live creds are provisioned.

## Cross-source conformance — the key idea

`silver_teams.external_id_mlbam` (and `silver_games.external_id_mlbam`) is the **MLBAM id** — the standard
cross-source join key in baseball data. Carrying it through to gold means this Synergy data lines up with
any other MLBAM-keyed source the customer has, on the same team and player ids.

## Notes & gotchas (learned running this)

- **Auth from a laptop:** Databricks Connect picks up auth from the SDK config chain. The cleanest path is
  a CLI OAuth profile (`databricks auth login`, then `DATABRICKS_CONFIG_PROFILE=<profile>`). A stale PAT in
  `.env` will override the profile and 403 — leave `DATABRICKS_TOKEN` blank if you use a profile.
- **Writing to the Volume over Connect:** the notebooks land JSON with the **SDK Files API**
  (`w.files.upload`), *not* local `open()`/`os` — a laptop has no `/Volumes` FUSE mount, so plain file I/O
  only works inside a Databricks cluster. (This is why `01_ingest` and `generate_fake_data` use `upload_json`.)
- **Bronze needs `cloudFiles.inferColumnTypes`:** without it Auto Loader reads nested JSON objects as
  *strings*, and every nested silver column (`league_name`, `home_team_name`, …) comes out NULL. It's set
  in `02_bronze_autoloader`.
- **Silver casts via `data:path::type`** (full-refresh `CREATE OR REPLACE`, since Spark Connect can't
  `MERGE`). If a messier live entity has junk values that hard-fail a cast, switch that column to
  `try_cast(data:path::string AS type)` (nulls bad values instead of erroring).

---

## For the SA finishing this

Ingestion is complete for all 19 entities; here's the runway to a customer-ready demo:

1. **Curate the wide tables** — `events` (272 cols) and `practice_events` (265 cols) are comprehensive
   (every scalar leaf in the spec). For the customer, the `events_pitch_subset` / `events_defense_subset` /
   `events_game_state_subset` tables are the leaner, ready-to-use views. Trim `SILVER_COLUMNS` if a slimmer
   `events` table is preferred.
2. **Extend the DQX checks (`04`)** — the gate ships with a key-not-null baseline. Add business rules
   (date ranges, enum membership, referential checks against your dims) so the customer's quarantine table
   reflects real quality issues.
3. **Build gold (`05`)** — `dim_team` is worked as a template. Add `dim_player` (from `players` /
   `players_teamhistory`), `dim_date`, `fact_game`, `fact_event`/`fact_pitch` (from the event tables).
   Declare RELY PK/FK constraints (worked example in `05`) so AI/BI + Genie can infer the joins.
4. **Genie + dashboard (`06`)** — build an AI/BI dashboard + Genie space over the gold schema (steps in the
   notebook). Set `SQL_WAREHOUSE_ID` and curate customer questions.
5. **Customer customization hooks:**
   - **Credentials** → the customer's Synergy `client_id`/`client_secret` (secret scope `synergy`).
   - **Scope** → `SYNERGY_START_DATE`/`END_DATE`/`SEASON` and any team/league filters in `01_ingest`.
   - **Branding** → dashboard title + Genie sample questions in `06`.

### Design note

The client, schemas, and notebooks are deliberately plain Python + SQL so the whole flow is easy to
follow and adapt. The API contract (OAuth, `POST /api/<entity>/filter` pagination) and the silver column
projections are all verified against the Synergy OpenAPI spec, so what runs here is what runs against the
live API once credentials are in place.

> ⚠️ **Never commit credentials.** `.env` is gitignored; real `client_id`/`client_secret` live only in
> `.env` (local) or the `synergy` secret scope (workspace).
