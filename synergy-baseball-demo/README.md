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
| `synergy_client.py` | ✅ | `SynergyAPI` — OAuth2 client-credentials + auto-paginated `POST /api/<entity>/filter`. |
| `synergy_schemas.py` | ✅ | `ENTITIES` registry (all 19) + `SILVER_COLUMNS` `(path, alias, type)` maps, verified against the OpenAPI spec. The extension point. |
| `00_verify_connection.ipynb` | ✅ | Spark + UC schemas/Volume + Synergy OAuth probe. **Run first.** |
| `01_ingest_synergy_api.ipynb` | ✅ | Loop every entity in `ENTITIES` → land JSON in the Volume (reference = pull all, date_scoped = windowed). |
| `02_bronze_autoloader.ipynb` | ✅ | Auto Loader JSON → `bronze_<entity>` (`data VARIANT`) for every entity. |
| `03_silver_transformations.ipynb` | ✅ | Shred VARIANT → typed `silver_<entity>` for every entity. |
| `04_gold_star_schema.ipynb` | 🟡 TODO | `dim_team` worked as a template; dims/facts for the SA to finish. |
| `05_genie_and_dashboard.ipynb` | 🟡 TODO | Plan for the AI/BI dashboard + Genie space over gold. |
| `tests/generate_fake_data.ipynb` | ✅ | Schema-driven synthetic data for **all** entities → run 02/03 **without credentials**. |
| `.env.example` | ✅ | Copy to `.env`. Creds resolve from `.env` or a `synergy` secret scope. |

**The 19 entities** (every bulk `/filter` endpoint in the spec): `teams`, `games`, `players`,
`players_teamhistory`, `events`, `events_pitch_subset`, `events_defense_subset`, `events_game_state_subset`,
`leagues`, `divisions`, `conferences`, `competitions`, `venues`, `umpires`, `practice_sessions`,
`practice_events`, `practice_training_workout`, `search_players`, `search_teams`. Excluded (not bulk data):
`*/filter-no-count` (redundant), `videos/sign` (utility), `GET /{id}` (single-record lookups).

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
                    04 🟡 (dim_team/dim_player/fact_game ...)
                          ▼
              {schema}_gold.*  ──▶ 05 🟡 Genie space + dashboard
```

**Why VARIANT, not `from_json`?** Synergy payloads are deeply nested and evolve; landing the whole row as
`data VARIANT` and navigating with `data:home_team:id::string` in silver means new fields never break
ingest — you opt into columns by adding them to `synergy_schemas.SILVER_COLUMNS`.

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
```

### No Synergy credentials yet?

Run **`tests/generate_fake_data.ipynb`** instead of `01`. It writes schema-driven synthetic data for **all
19 entities** into the Volume, then `02` → `03` work end-to-end offline. Perfect for kicking the tires
before live creds are provisioned.

## Cross-source conformance — the key idea

`silver_teams.external_id_mlbam` (and `silver_games.external_id_mlbam`) is the **MLBAM id** — the same key
the broader MLB warehouse joins on (`statsapi.silver.teams`, `gold.dim_team`). That's the hook that ties
Synergy into everything else for the customer: pitch/event data keyed to the same teams and players as
Statcast, GUMBO, and the rest.

---

## For the SA finishing this

Ingestion is complete for all 19 entities; here's the runway to a customer-ready demo:

1. **Curate the wide tables** — `events` (272 cols) and `practice_events` (265 cols) are comprehensive
   (every scalar leaf in the spec). For the customer, the `events_pitch_subset` / `events_defense_subset` /
   `events_game_state_subset` tables are the leaner, ready-to-use views. Trim `SILVER_COLUMNS` if a slimmer
   `events` table is preferred.
2. **Build gold (`04`)** — `dim_team` is worked as a template. Add `dim_player` (from `players` /
   `players_teamhistory`), `dim_date`, `fact_game`, `fact_event`/`fact_pitch` (from the event tables).
   Declare RELY PK/FK constraints (worked example in `04`) so AI/BI + Genie can infer the joins.
3. **Genie + dashboard (`05`)** — build an AI/BI dashboard + Genie space over the gold schema (steps in the
   notebook). Set `SQL_WAREHOUSE_ID` and curate customer questions.
4. **Customer customization hooks:**
   - **Credentials** → the customer's Synergy `client_id`/`client_secret` (secret scope `synergy`).
   - **Scope** → `SYNERGY_START_DATE`/`END_DATE`/`SEASON` and any team/league filters in `01_ingest`.
   - **Branding** → dashboard title + Genie sample questions in `05`.

### Provenance

`synergy_client.py` and the silver column maps are ported from the production-grade, config-driven
`mlb_pipelines` Synergy accelerator (the DABs medallion). This demo trades that engine for plain
follow-along notebooks — the API contract, pagination, and projections are the same, so anything proven
here lifts straight back into the accelerator (and vice-versa).

> ⚠️ **Never commit credentials.** `.env` is gitignored; real `client_id`/`client_secret` live only in
> `.env` (local) or the `synergy` secret scope (workspace).
