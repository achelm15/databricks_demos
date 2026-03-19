# Ticketmaster Event Analytics

Medallion architecture demo using the Ticketmaster Discovery API. Ingests live event data, lands raw JSON in Unity Catalog Volumes, and builds a full Bronze → Silver → Gold star schema — all from local Jupyter notebooks via Databricks Connect (serverless).

## What's Covered

- **API ingestion** → UC Volume landing zone (date-partitioned JSON files)
- **Auto Loader** (batch mode) → VARIANT bronze tables
- **MERGE deduplication** with MD5 surrogate keys → Silver normalized tables
- **Star schema** (Type 1 dimensions, fact table, bridge table) → Gold layer
- **PK/FK constraints**, liquid clustering, materialized views
- **Analytical queries** against the gold star schema

## Prerequisites

1. A Databricks workspace with Unity Catalog enabled
2. A Ticketmaster API key ([get one here](https://developer.ticketmaster.com/))
3. Python 3.10+

## Setup

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # fill in your values
jupyter notebook
```

## Notebook Flow

| Notebook | Purpose |
|----------|---------|
| `00_verify_connection` | Confirm serverless connectivity, create catalog/schemas |
| `01_ingest_ticketmaster_api` | Fetch events/venues/attractions/classifications → Volume |
| `02_bronze_layer` | Auto Loader → VARIANT Delta tables |
| `03_silver_transformations` | VARIANT extraction, MERGE dedup, PK/FK constraints |
| `04_gold_star_schema` | Dimensions, fact table, bridge table, materialized views |
| `05_analyze_and_query` | Analytical queries, data quality checks, optional cleanup |

Run them sequentially: 00 → 01 → 02 → 03 → 04 → 05.

## Data Model

```
Gold Star Schema:

dim_date ──────┐
dim_venue ─────┤
dim_classification─┤── fact_events
               │
dim_attraction ┤── bridge_event_attractions ── fact_events
```

## Simplified from [tix-master](https://github.com/tjwaggoner/tix-master)

- No DABs, jobs, or stored procedures — just sequential notebooks
- `.env` instead of Databricks secrets
- VARIANT bronze tables instead of schema inference
- Batch MERGE instead of Structured Streaming
- Type 1 dimensions instead of SCD Type 2
