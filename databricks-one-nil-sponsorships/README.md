# Databricks One — NIL Sponsorship Analytics

A full Databricks One demo built around college athlete NIL (Name, Image, Likeness) sponsorship data. Builds a governed medallion architecture from scratch, creates an AI/BI dashboard and Genie space programmatically, then walks through setting up Domains and the Discover page — all from local Jupyter notebooks via **Databricks Connect** (serverless compute).

## Overview

This demo showcases the end-to-end journey from raw data to governed business intelligence on Databricks:

- **Synthetic data generation** → Athletes, sponsors, deals, and campaigns via Faker
- **Bronze layer** → Auto Loader (batch mode) loads JSON into VARIANT-based Delta tables
- **Silver layer** → Typed extraction, MD5 surrogate keys, full refresh via `INSERT OVERWRITE`
- **Gold layer** → Star schema with dimensions, facts, and analytical views
- **Catalog enrichment** → Comments, tags (domain, tier, PII), lineage verification
- **AI/BI Dashboard** → Created and published via Lakeview API
- **Genie Space** → Created via API with sample questions and NIL terminology
- **Discover + Domains** → Step-by-step UI walkthrough for the Databricks One experience

> **Databricks Connect note:** This demo uses `INSERT OVERWRITE` instead of `MERGE` for Silver and Gold loads. `MERGE` is not supported when running via Databricks Connect (Spark Connect).

## Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│  01_generate_nil_data                                                       │
│  Faker → UC Volume (raw_data/athletes|sponsors|deals|campaigns)            │
└─────────────────────────────────────┬───────────────────────────────────────┘
                                      │
                                      ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│  BRONZE (02_bronze_ingestion)                                               │
│  Auto Loader → VARIANT Delta tables                                         │
│  athletes_raw, sponsors_raw, deals_raw, campaigns_raw                      │
└─────────────────────────────────────┬───────────────────────────────────────┘
                                      │
                                      ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│  SILVER (03_silver_transformations)                                         │
│  data:field::type extraction, MD5 surrogate keys, INSERT OVERWRITE          │
│  athletes, sponsors, deals, campaigns                                      │
└─────────────────────────────────────┬───────────────────────────────────────┘
                                      │
                                      ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│  GOLD (04_gold_layer)                                                       │
│  Star schema: dim_athlete, dim_sponsor, dim_date,                           │
│               fact_deals, fact_campaign_performance + 3 analytical views    │
└─────────────────────────────────────┬───────────────────────────────────────┘
                                      │
                                      ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│  ENRICHMENT (05_catalog_enrichment)                                         │
│  COMMENT ON, SET TAGS, information_schema verification, lineage queries    │
└─────────────────────────────────────┬───────────────────────────────────────┘
                                      │
                                      ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│  DATABRICKS ONE (06 + 07 + 08)                                              │
│  Lakeview dashboard, Genie space, Discover page + Domains walkthrough      │
└─────────────────────────────────────────────────────────────────────────────┘
```

## Data Model (Gold Star Schema)

```
              dim_date
                 │
            dim_athlete ──── fact_deals ──── dim_sponsor
                                │
                    fact_campaign_performance
```

| Table | Description | Primary Key |
|-------|-------------|-------------|
| `dim_date` | Date dimension (2024–2027) | `date_sk` |
| `dim_athlete` | College athletes (school, sport, social following) | `athlete_sk` |
| `dim_sponsor` | Sponsor brands (industry, budget tier, region) | `sponsor_sk` |
| `fact_deals` | One row per NIL contract | `deal_sk` |
| `fact_campaign_performance` | One row per campaign event | `campaign_sk` |

**Views:** `v_athlete_deal_leaderboard`, `v_sponsor_roi`, `v_conference_summary`

## Prerequisites

| Requirement | Details |
|-------------|---------|
| **Databricks workspace** | Unity Catalog enabled, Serverless compute available |
| **SQL Warehouse** | Pro or Serverless (for dashboard + Genie) |
| **Python** | 3.10 or higher |
| **Databricks Connect** | Must match workspace DBR version (see `requirements.txt`) |
| **Account admin** (for Discover) | To enable Domains and Discover Page preview |

## Setup

### 1. Clone and create environment

```bash
cd databricks-one-nil-sponsorships
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

Run notebooks in order: **00 → 01 → 02 → 03 → 04 → 05 → 06 → 07 → 08** (08 is a UI guide).

## Configuration

Create a `.env` file (gitignored) with the following variables:

| Variable | Required | Description |
|----------|----------|-------------|
| `DATABRICKS_HOST` | Yes | Workspace URL, e.g. `https://your-workspace.cloud.databricks.com` |
| `DATABRICKS_TOKEN` | Yes | Personal access token or OAuth token |
| `DATABRICKS_CLUSTER_ID` | No | Leave blank to use **Serverless** compute (recommended) |
| `UC_CATALOG` | Yes | Unity Catalog catalog name (e.g. `main` or your user catalog) |
| `UC_SCHEMA` | Yes | Base schema name; creates `{schema}_bronze`, `{schema}_silver`, `{schema}_gold` |
| `SQL_WAREHOUSE_ID` | Yes | SQL Warehouse ID (for dashboard + Genie creation in notebooks 06–07) |

## Notebook Flow

| # | Notebook | Purpose |
|---|----------|---------|
| 00 | `00_verify_connection` | Verify Databricks Connect, create catalog/schemas |
| 01 | `01_generate_nil_data` | Generate synthetic athletes, sponsors, deals, campaigns → UC Volume |
| 02 | `02_bronze_ingestion` | Auto Loader (batch) → VARIANT Delta tables |
| 03 | `03_silver_transformations` | Extract typed columns, MD5 keys, INSERT OVERWRITE, PK/FK |
| 04 | `04_gold_layer` | Build star schema, dimensions, fact tables, views |
| 05 | `05_catalog_enrichment` | Add comments, tags (domain/tier/PII/owner), verify lineage |
| 06 | `06_create_dashboard` | Create + publish AI/BI (Lakeview) dashboard via API |
| 07 | `07_create_genie_space` | Create Genie space via API with sample questions + instructions |
| 08 | `08_discover_walkthrough` | **UI guide:** enable previews, create domain, certify assets, Databricks One |

## Discover Page & Databricks One Setup (Notebook 08)

After running notebooks 00–07, follow the UI walkthrough in notebook 08:

1. **Enable previews** — Account: "Domains and Discover Page"; Workspace: "Discover Page"
2. **Create governed tag** — `nil_sponsorships` in Catalog > Governed Tags
3. **Create domain** — "NIL Sponsorships" on the Discover page, backed by the governed tag
4. **Add assets** — dashboard, Genie space, and gold tables to the domain
5. **Organize sections** — curate the domain page with custom groups
6. **Certify assets** — badge the dashboard, Genie space, and key tables
7. **Enable anomaly detection** — on the gold schema for health indicators
8. **AI descriptions** — trigger in Catalog Explorer for enhanced search/Genie accuracy
9. **Demo as consumer** — switch to Databricks One view or use a consumer-only user

## Key Implementation Details

- **VARIANT bronze:** Raw JSON stored as `data VARIANT`; extraction uses `data:field::type` syntax
- **Surrogate keys:** MD5 hashes for deduplication (e.g. `athlete_sk = MD5(athlete_id)`)
- **Liquid clustering:** `deals` (Silver) and `fact_deals` / `fact_campaign_performance` (Gold)
- **RELY constraints:** Primary and foreign keys are informational (RELY) for optimizer hints
- **Tags:** `domain`, `tier`, `data_owner` on tables; `pii`, `sensitivity` on columns
- **Dashboard API:** Created via `w.lakeview.create()` + `w.lakeview.publish()`
- **Genie API:** Created via `w.genie.create_space()` with serialized config

## Troubleshooting

| Issue | Solution |
|-------|----------|
| `SQL_WAREHOUSE_ID not set` | Add your warehouse ID to `.env` (find under SQL Warehouses > Connection details) |
| Discover page not visible | Enable "Discover Page" preview in workspace settings |
| "Create domain" button missing | Need `MANAGE_DISCOVERY` permission (account admin grants this) |
| Dashboard not showing in Databricks One | Ensure it's published (notebook 06 does this) and user has access |
| Genie not answering questions | Verify warehouse is running and user has `SELECT` on gold tables |
| Tags not appearing in Discover | May need governed tag (Step 2 in notebook 08) for domain membership |
| Databricks Connect version mismatch | Align `databricks-connect` in `requirements.txt` with workspace DBR version |

## Cleanup

1. Delete Genie space, dashboard, domain, and governed tag via the UI
2. Run the reset cell in notebook 00 or 08 to drop all schemas
