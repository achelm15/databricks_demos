# Synergy Baseball — Databricks Medallion Demo (Starter)

A **follow-along, notebook-style** demo that ingests [Synergy Sports Baseball](https://synergysports.com/)
data into a Databricks medallion (bronze → silver → gold) on Unity Catalog. Dual-mode notebooks (run from a
laptop via Databricks Connect *or* inside a Databricks Git Folder), Auto Loader bronze, VARIANT-shredded
silver.

> **This is a STARTER for handoff.** The framework + a worked example (teams + games) run end-to-end
> through Silver. Gold and the Genie/dashboard layer are scaffolded as `🟡 TODO` stubs for the receiving
> SA to finish for the customer. See **[For the SA finishing this](#for-the-sa-finishing-this)** below.

---

## What's here

| File | Status | What it does |
|---|---|---|
| `synergy_client.py` | ✅ | `SynergyAPI` — OAuth2 client-credentials + auto-paginated `POST /api/<entity>/filter`. `get_teams()`, `get_games()`. |
| `synergy_schemas.py` | ✅ | `ENTITIES` registry + `SILVER_COLUMNS` `(path, alias, type)` maps for **teams** + **games**. The extension point. |
| `00_verify_connection.ipynb` | ✅ | Spark + UC schemas/Volume + Synergy OAuth probe. **Run first.** |
| `01_ingest_synergy_api.ipynb` | ✅ | Pull teams (reference) + games (date window) → land JSON in the Volume. |
| `02_bronze_autoloader.ipynb` | ✅ | Auto Loader JSON → `bronze_<entity>` (`data VARIANT`). |
| `03_silver_transformations.ipynb` | ✅ | Shred VARIANT → typed `silver_teams`, `silver_games`. |
| `04_gold_star_schema.ipynb` | 🟡 TODO | `dim_team` worked as a template; dims/facts for the SA to finish. |
| `05_genie_and_dashboard.ipynb` | 🟡 TODO | Plan for the AI/BI dashboard + Genie space over gold. |
| `tests/generate_fake_data.ipynb` | ✅ | Synthetic teams/games → run 02/03 **without credentials**. |
| `.env.example` | ✅ | Copy to `.env`. Creds resolve from `.env` or a `synergy` secret scope. |

## The data flow

```
Synergy API ──01──▶ /Volumes/.../raw_data/{teams,games}/*.json
                          │
                    02 (Auto Loader, cloudFiles JSON → VARIANT)
                          ▼
              {schema}_bronze.bronze_{teams,games}   (data VARIANT + _ingestion_timestamp)
                          │
                    03 (data:path::type, dedup to natural key)
                          ▼
              {schema}_silver.silver_{teams,games}   (typed, conformed)
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
01_ingest_synergy_api     →  pulls teams + games into the Volume
02_bronze_autoloader      →  Auto Loads them to bronze
03_silver_transformations →  builds typed silver_teams, silver_games
```

### No Synergy credentials yet?

Run **`tests/generate_fake_data.ipynb`** instead of `01`. It writes synthetic teams + games (matching the
Synergy `result` row shape) into the Volume, then `02` → `03` work end-to-end offline. Perfect for kicking
the tires before live creds are provisioned.

## Cross-source conformance — the key idea

`silver_teams.external_id_mlbam` is the **MLBAM team id** — the same key the broader MLB warehouse joins on
(`statsapi.silver.teams`, `gold.dim_team`). That's the hook that ties Synergy into everything else for the
customer: pitch/event data keyed to the same teams and players as Statcast, GUMBO, and the rest.

---

## For the SA finishing this

The framework is done; here's the runway to a customer-ready demo:

1. **Fan out entities** — the customer will want more than teams + games (players, venues, events, pitch
   subsets). For each: register it in `synergy_schemas.ENTITIES`, add its `SILVER_COLUMNS` map (copy the
   projection straight from the `mlb_pipelines` accelerator — `src/synergy/<entity>/endpoint.yml`), and add
   a pull in `01_ingest`. `02`/`03` pick it up automatically from the registry.
2. **Build gold (`04`)** — `dim_team` is worked as a template. Add `dim_player`, `dim_date`, `fact_game`,
   and (once events are ingested) `fact_event`/`fact_pitch`. Declare RELY PK/FK constraints (worked example
   in `04`) so AI/BI + Genie can infer the joins.
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
