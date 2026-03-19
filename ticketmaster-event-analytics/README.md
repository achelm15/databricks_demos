# Ticketmaster Event Analytics

A medallion architecture demo that ingests live event data from the [Ticketmaster Discovery API](https://developer.ticketmaster.com/products-and-docs/apis/discovery-api/v2/), lands raw JSON in Unity Catalog Volumes, and builds a full Bronze → Silver → Gold star schema — all from local Jupyter notebooks via **Databricks Connect** (serverless compute).

## Overview

This demo showcases a production-style data pipeline on Databricks:

- **API ingestion** → Raw JSON files landed in a UC Volume (date-partitioned)
- **Bronze layer** → Auto Loader (batch mode) loads JSON into VARIANT-based Delta tables
- **Silver layer** → Typed extraction, MD5 surrogate keys, full refresh via `INSERT OVERWRITE`
- **Gold layer** → Star schema with Type 1 dimensions, fact table, bridge table, and analytical views
- **Constraints** → Primary keys, foreign keys (RELY), liquid clustering for query performance

> **Databricks Connect note:** This demo uses `INSERT OVERWRITE` instead of `MERGE` for Silver and Gold loads. `MERGE` is not supported when running via Databricks Connect (Spark Connect). For full refresh pipelines, `INSERT OVERWRITE` is equivalent and works reliably.

## Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│  Ticketmaster Discovery API                                                 │
│  (events, venues, attractions, classifications)                             │
└─────────────────────────────────────┬───────────────────────────────────────┘
                                      │
                                      ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│  01_ingest_ticketmaster_api                                                  │
│  REST API → UC Volume (raw_data/events|venues|attractions|classifications)  │
└─────────────────────────────────────┬───────────────────────────────────────┘
                                      │
                                      ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│  BRONZE (02_bronze_layer)                                                   │
│  Auto Loader → VARIANT Delta tables                                         │
│  events_raw, venues_raw, attractions_raw, classifications_raw             │
└─────────────────────────────────────┬───────────────────────────────────────┘
                                      │
                                      ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│  SILVER (03_silver_transformations)                                         │
│  data:field::type extraction, MD5 surrogate keys, INSERT OVERWRITE          │
│  venues, attractions, classifications, events, event_attractions            │
└─────────────────────────────────────┬───────────────────────────────────────┘
                                      │
                                      ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│  GOLD (04_gold_star_schema)                                                 │
│  Star schema: dim_date, dim_venue, dim_attraction, dim_classification,       │
│               fact_events, bridge_event_attractions + 3 analytical views    │
└─────────────────────────────────────────────────────────────────────────────┘
```

## Data Model (Gold Star Schema)

```
                    dim_date
                         │
                    dim_venue ────────┐
                         │            │
              dim_classification ─────┼──── fact_events
                         │            │
                    dim_attraction ───┘
                         │
                         └──── bridge_event_attractions ──── fact_events
```

| Table | Description | Primary Key |
|-------|-------------|-------------|
| `dim_date` | Date dimension (2024–2027) | `date_sk` |
| `dim_venue` | Venue locations (Type 1) | `venue_sk` |
| `dim_attraction` | Artists/performers (Type 1) | `attraction_sk` |
| `dim_classification` | Event categories (Type 1) | `classification_sk` |
| `fact_events` | One row per event | `event_sk` |
| `bridge_event_attractions` | Many-to-many event ↔ attraction | `(event_sk_fk, attraction_sk_fk)` |

**Views:** `v_events_by_date_venue`, `v_events_by_attraction`, `v_monthly_summary`

## Prerequisites

| Requirement | Details |
|-------------|---------|
| **Databricks workspace** | Unity Catalog enabled, Serverless compute available |
| **Ticketmaster API key** | Free at [developer.ticketmaster.com](https://developer.ticketmaster.com/) |
| **Python** | 3.10 or higher |
| **Databricks Connect** | Must match workspace DBR version (see `requirements.txt`) |

## Setup

### 1. Clone and create environment

```bash
cd ticketmaster-event-analytics
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

### 2. Configure environment

```bash
cp .env.example .env
# Edit .env with your values (see Configuration below)
```

### 3. Run notebooks

```bash
jupyter notebook
# Or: jupyter lab
```

Run notebooks in order: **00 → 01 → 02 → 03 → 04 → 05**.

## Configuration

Create a `.env` file (gitignored) with the following variables:

| Variable | Required | Description |
|----------|----------|-------------|
| `DATABRICKS_HOST` | Yes | Workspace URL, e.g. `https://your-workspace.cloud.databricks.com` |
| `DATABRICKS_TOKEN` | Yes | Personal access token or OAuth token |
| `DATABRICKS_CLUSTER_ID` | No | Leave blank to use **Serverless** compute (recommended) |
| `UC_CATALOG` | Yes | Unity Catalog catalog name (e.g. `main` or your user catalog) |
| `UC_SCHEMA` | Yes | Base schema name; creates `{schema}_bronze`, `{schema}_silver`, `{schema}_gold` |
| `TICKETMASTER_API_KEY` | Yes | API key from [developer.ticketmaster.com](https://developer.ticketmaster.com/) |

**Example `.env`:**

```env
DATABRICKS_HOST=https://your-workspace.cloud.databricks.com
DATABRICKS_TOKEN=dapiXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX
DATABRICKS_CLUSTER_ID=

UC_CATALOG=main
UC_SCHEMA=ticketmaster_demo

TICKETMASTER_API_KEY=your_api_key_here
```

## Notebook Flow

| # | Notebook | Purpose |
|---|----------|---------|
| 00 | `00_verify_connection` | Verify Databricks Connect, create catalog/schemas |
| 01 | `01_ingest_ticketmaster_api` | Fetch events, venues, attractions, classifications → UC Volume |
| 02 | `02_bronze_layer` | Auto Loader (batch) → VARIANT Delta tables |
| 03 | `03_silver_transformations` | Extract typed columns, MD5 keys, INSERT OVERWRITE, PK/FK |
| 04 | `04_gold_star_schema` | Build star schema, dimensions, fact table, bridge, views |
| 05 | `05_analyze_and_query` | Sample queries, lineage checks, data quality, optional cleanup |

**Execution order:** Run 00–05 sequentially. Notebook 01 must complete before 02; 02 before 03; etc.

## Key Implementation Details

- **VARIANT bronze:** Raw JSON stored as `data VARIANT`; extraction uses `data:field::type` syntax
- **Surrogate keys:** MD5 hashes for deduplication (e.g. `venue_sk = MD5(venue_id)`)
- **Liquid clustering:** `events` (Silver) and `fact_events` (Gold) use `CLUSTER BY` for query performance
- **RELY constraints:** Primary and foreign keys are informational (RELY) for optimizer hints and ERD tools
- **Full refresh:** Silver and Gold use `INSERT OVERWRITE` for idempotent, repeatable loads

## Troubleshooting

| Issue | Solution |
|-------|----------|
| `UnsupportedOperationException` on MERGE | Ensure you're using the updated notebooks with `INSERT OVERWRITE` (not MERGE) |
| `TICKETMASTER_API_KEY not set` | Add your API key to `.env` |
| Databricks Connect version mismatch | Align `databricks-connect` in `requirements.txt` with your workspace DBR version |
| Schema/table not found | Run `00_verify_connection` first; ensure `UC_CATALOG` and `UC_SCHEMA` match |
| Empty gold tables | Run 01 (ingest) → 02 (bronze) → 03 (silver) → 04 (gold) in order |

## Simplified from [tix-master](https://github.com/tjwaggoner/tix-master)

- No DABs, jobs, or stored procedures — sequential notebooks only
- `.env` for configuration instead of Databricks secrets
- VARIANT bronze tables instead of schema inference
- Batch `INSERT OVERWRITE` instead of Structured Streaming
- Type 1 dimensions (overwrite) instead of SCD Type 2
