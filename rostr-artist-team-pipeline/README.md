# rostr-artist-team-pipeline

Medallion-architecture accelerator that lands the **rostr.cc** music-industry
API into Unity Catalog as governed Bronze → Silver → Gold tables, then builds
an AI/BI dashboard on top.

This is the "real Databricks engineering" sibling to
[`rostr-artist-team-enrichment/`](../rostr-artist-team-enrichment/) (which is a
Google-Sheet-driven flow). Same source system, totally different downstream:
no sheets here — everything lands in UC.

## Overview

- **Two API routes** drive the pipeline:
    - `GET /v1/artist/{handle}` — full artist record (~60 fields incl. AI bio + social metric snapshots)
    - `GET /v1/artist/{handle}/team/{ROLE}` for `MANAGEMENT, AGENCY, RECORD_LABEL, PUBLISHER` — the company × people graph for that artist
- **Seed list** of artists in `artists_seed.csv` (override the slug per row if you need to)
- **Idempotent ingest** — files already in the Volume are skipped, so re-runs only call rostr.cc for missing data. `FORCE_REFRESH=true` opts back into a full pull.
- **VARIANT bronze** — raw JSON lands as `data VARIANT`, navigable with `data:field::type`. PySpark schemas in `rostr_schemas.py` are the canonical reference for silver extraction.
- **Silver normalized model** — `silver_artists`, `silver_companies`, `silver_company_people`, `silver_artist_company` (M:N bridge), `silver_artist_person`. MD5 surrogate keys, RELY PK/FK, liquid clustering.
- **Star-schema gold** — `dim_artist`, `dim_company`, `dim_person`, `fact_artist_team` plus four pre-aggregated views ready for AI/BI and Genie.
- **Dual-mode** — same notebooks run from a laptop *and* in a Databricks Git Folder. Secrets resolve from `.env` first, then fall back to a workspace secret scope (`rostr`).

> **Databricks Connect note.** Silver and Gold use `INSERT OVERWRITE` instead of `MERGE` — `MERGE` isn't supported through Spark Connect. If you run the notebooks inside a Databricks workspace cluster, you can swap `INSERT OVERWRITE` for `MERGE` to get incremental loads; the schema is identical.

## Architecture

```
┌────────────────────────────────────────────────────────────────────────────┐
│  rostr.cc API  (api.rostr.cc)                                              │
│  Two routes: /v1/artist/{handle}  +  /v1/artist/{handle}/team/{ROLE} x4    │
└──────────────────────────────────┬─────────────────────────────────────────┘
                                   │
                                   ▼
┌────────────────────────────────────────────────────────────────────────────┐
│  01_ingest_rostr_api                                                        │
│  Seed CSV → per-artist fan-out → UC Volume raw_data/                       │
│  artists/{handle}.json   team/{handle}/{ROLE}.json (4 per artist)           │
└──────────────────────────────────┬─────────────────────────────────────────┘
                                   │
                                   ▼
┌────────────────────────────────────────────────────────────────────────────┐
│  BRONZE (02_bronze_autoloader)                                              │
│  Auto Loader (availableNow) → 2 VARIANT-typed Delta tables                  │
│    bronze_artists  bronze_team                                              │
└──────────────────────────────────┬─────────────────────────────────────────┘
                                   │
                                   ▼
┌────────────────────────────────────────────────────────────────────────────┐
│  SILVER (03_silver_transformations)                                         │
│  data:field::type extraction + from_json + LATERAL VIEW EXPLODE             │
│  MD5 SKs, RELY PK/FK, liquid clustering, INSERT OVERWRITE                   │
│  silver_artists   silver_companies   silver_company_people                  │
│  silver_artist_company   silver_artist_person                               │
└──────────────────────────────────┬─────────────────────────────────────────┘
                                   │
                                   ▼
┌────────────────────────────────────────────────────────────────────────────┐
│  GOLD (04_gold_star_schema)                                                 │
│  dim_artist / dim_company / dim_person / fact_artist_team                   │
│  v_agency_market_share / v_top_managers /                                   │
│  v_artists_by_label / v_artist_team_summary                                 │
└──────────────────────────────────┬─────────────────────────────────────────┘
                                   │
                                   ▼
┌────────────────────────────────────────────────────────────────────────────┐
│  DASHBOARD (05_create_dashboard) — Lakeview / AI/BI                          │
│  3 KPI counters + agency pie + top-managers table +                          │
│  Spotify-followers bar + label-leaders bar                                   │
└────────────────────────────────────────────────────────────────────────────┘
```

## Files

| File | Purpose |
|---|---|
| `00_verify_connection.ipynb` | Spark, UC, rostr login probe |
| `01_ingest_rostr_api.ipynb`  | Seed CSV → API → UC Volume (idempotent) |
| `02_bronze_autoloader.ipynb` | Auto Loader → VARIANT bronze tables |
| `03_silver_transformations.ipynb` | Typed silver model + RELY constraints |
| `04_gold_star_schema.ipynb`  | Star schema + analytical views |
| `05_create_dashboard.ipynb`  | Lakeview AI/BI dashboard creation |
| `rostr_client.py`            | Thin client (login + 2 endpoints). Same module as the enrichment demo. |
| `rostr_schemas.py`           | PySpark `StructType` reference + inline DDL strings used by silver |
| `artists_seed.csv`           | The list of artists to ingest. Edit freely. |
| `requirements.txt`, `.env.example` | Standard demo scaffolding |

## Setup

```bash
cd rostr-artist-team-pipeline
pip install -r requirements.txt          # databricks-connect, requests, python-dotenv
cp .env.example .env
# Fill in:
#   DATABRICKS_HOST/TOKEN, UC_CATALOG/UC_SCHEMA
#   ROSTR_USERNAME/PASSWORD
#   SQL_WAREHOUSE_ID  (only required for 05_create_dashboard.ipynb)
```

Then run the notebooks in order:

```
00_verify_connection.ipynb
01_ingest_rostr_api.ipynb
02_bronze_autoloader.ipynb
03_silver_transformations.ipynb
04_gold_star_schema.ipynb
05_create_dashboard.ipynb       # optional
```

## Sample analytical queries

```sql
-- Who manages the most artists in the seed list?
SELECT person_name, company_name, artist_count
FROM alexander_booth.rostr_music_industry_gold.v_top_managers
LIMIT 10;

-- Agency market share across the seed
SELECT * FROM alexander_booth.rostr_music_industry_gold.v_agency_market_share;

-- Wide artist team summary (sheet-style row per artist, but as a Delta view)
SELECT artist_name, agencies, management_firms, labels, publishers
FROM alexander_booth.rostr_music_industry_gold.v_artist_team_summary;

-- Cross-check against social-platform reach
SELECT a.artist_name, a.spotify_followers,
       COLLECT_SET(c.company_name) FILTER (WHERE ac.role = 'AGENCY')     AS agency,
       COLLECT_SET(c.company_name) FILTER (WHERE ac.role = 'MANAGEMENT') AS mgmt
FROM alexander_booth.rostr_music_industry_gold.dim_artist a
LEFT JOIN alexander_booth.rostr_music_industry_silver.silver_artist_company ac
       ON ac.artist_handle = a.artist_handle
LEFT JOIN alexander_booth.rostr_music_industry_silver.silver_companies c
       ON c.rostr_id = ac.company_rostr_id
GROUP BY a.artist_name, a.spotify_followers
ORDER BY a.spotify_followers DESC NULLS LAST;
```

## Demo flow (~10 min)

1. Show `artists_seed.csv` — 30 artists.
2. Run `00_verify_connection.ipynb` → green checks.
3. Run `01_ingest_rostr_api.ipynb` → watch the per-artist fan-out land 30 artist files + 120 team files in the Volume.
4. Run `02_bronze_autoloader.ipynb` → Auto Loader (availableNow) → 2 VARIANT bronze tables.
5. Run `03_silver_transformations.ipynb` → typed silver, RELY constraints visible in Catalog Explorer.
6. Run `04_gold_star_schema.ipynb` → star schema; preview `v_agency_market_share` and `v_top_managers`.
7. Run `05_create_dashboard.ipynb` → published Lakeview dashboard with the 6-widget layout.
8. (Optional) Open Catalog Explorer and walk the dim/fact lineage; show liquid clustering on `fact_artist_team(role)`.
