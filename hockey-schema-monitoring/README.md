# Hockey Schema Monitoring — Alerts, Monitoring, and Schema Evolution

A standalone Databricks demo that wires together three things customers usually want to see together:

1. **Schema drift alerts** — catch the case where an upstream API quietly adds new JSON keys
2. **Lakehouse Monitoring** — track freshness, row counts, and drift on the typed silver table
3. **Schema evolution** — absorb the new keys into silver without rewriting downstream code

The data is synthetic NHL play-by-play events. Bronze stores raw API responses as **VARIANT**; silver projects known keys into typed columns. When the "API" version bumps and adds new fields, the drift detector catches it before a strict downstream consumer breaks.

> **What this is *not*:** This is not pure Lakehouse Monitoring. LHM is great for column-level drift and freshness on a *known* schema, but it doesn't notice when an API starts returning new top-level keys you don't yet have columns for. That gap is what the drift detector + DBSQL alert covers.

## The four signals

| Signal | Where it fires | What triggers it |
|---|---|---|
| **DBSQL Alert** — unknown keys in bronze VARIANT | Email + DBSQL Alerts page | New top-level keys appear in `bronze.plays_raw.payload` that aren't in the known-keys allow-list |
| **Lakehouse Monitoring** drift dashboard | `<silver>_monitoring` dashboard, refreshed on schedule | Freshness slip, row-count delta, distribution drift on `silver.plays` |
| **Job alert** — strict silver fails | Email from the Jobs UI | A strict-mode silver projection job fails because incoming bronze has a key it can't cast |
| **Schema evolution** absorbs new keys | Silver table widens; downstream re-runs cleanly | After triage, we add the new keys to the known list and re-run silver with `mergeSchema=true` |

## Notebook flow

| # | Notebook | What it does |
|---|---|---|
| 00 | `00_setup.ipynb` | Verify Databricks Connect, create bronze/silver schemas |
| 01 | `01_bronze_variant_v1.ipynb` | Generate "v1" NHL play-by-play events as VARIANT in `bronze.plays_raw` |
| 02 | `02_silver_projection.ipynb` | Project known keys into typed `silver.plays` |
| 03 | `03_drift_detector_and_monitoring.ipynb` | Build the drift-detector query, expose it as a view, create a Lakehouse Monitor on `silver.plays` |
| 04 | `04_simulate_api_v2.ipynb` | Append "v2" events with new keys (`expected_goals`, `shot_quality_index`, `puck_speed_mph`) — drift detector now lights up |
| 05 | `05_schema_evolution.ipynb` | Widen the known-keys list, evolve silver with `mergeSchema=true`, re-run projection |

Run **00 → 01 → 02 → 03** to set up the demo, then drive **04 → 05** live as the "API change → alert → recovery" story.

## UI walkthrough

See **[`DEMO.md`](DEMO.md)** for the click-by-click flow through the Databricks UI:

- Catalog Explorer view of the VARIANT bronze table
- DBSQL Alerts page — create alert from `alerts/drift_alert.sql`, trigger by running notebook 04
- Lakehouse Monitoring dashboard for `silver.plays`
- Jobs UI — strict-silver job with `email_notifications.on_failure`

## Setup

```bash
cd hockey-schema-monitoring
conda activate demo-env   # or: python -m venv .venv && source .venv/bin/activate && pip install -r requirements.txt
cp .env.example .env      # fill in DATABRICKS_HOST / TOKEN / UC_CATALOG / ALERT_EMAIL
```

Run **`00_setup` → `01` → `02` → `03`** once to stand up the demo. Then for the live demo, run **`04`** and **`05`** in front of the audience.

## Configuration (`.env`)

| Variable | Required | Default | Notes |
|---|---|---|---|
| `DATABRICKS_HOST` | yes | — | `https://<workspace>.cloud.databricks.com` |
| `DATABRICKS_TOKEN` | yes | — | PAT or OAuth |
| `DATABRICKS_CLUSTER_ID` | no | _blank_ | leave blank for **Serverless** |
| `UC_CATALOG` | no | `alexander_booth` | catalog to create schemas in |
| `UC_SCHEMA` | no | `hockey_schema_monitoring` | base name; creates `_bronze` / `_silver` |
| `MONITORING_SCHEMA` | no | `<silver>_monitoring` | where Lakehouse Monitoring writes its tables |
| `ALERT_EMAIL` | no | — | shown in the alert + job-config snippets |
| `N_GAMES` | no | `8` | synthetic NHL games |
| `EVENTS_PER_GAME` | no | `400` | events per game |

## Why VARIANT in bronze?

NHL EDGE-style play-by-play APIs return JSON with a stable core (game id, period, event type, coords) plus an ever-growing tail of advanced-stats fields. **VARIANT** lets bronze land the raw payload without committing to a schema, while still being queryable with `payload:expected_goals::double` style dot-paths. That's what makes the "new key appears" case detectable in SQL without re-parsing JSON.

## Why allow-list-gated silver instead of auto schema evolution?

Databricks supports several flavors of automatic schema evolution. Any of them would let a new API key turn into a silver column with no human in the loop:

| Mechanism | Behavior |
|---|---|
| `df.write.option('mergeSchema', 'true')` | New columns in the DataFrame are appended to the target Delta table on write |
| `spark.databricks.delta.schema.autoMerge.enabled = true` | Same, but session-wide — every write absorbs new columns |
| Auto Loader `cloudFiles.schemaEvolutionMode = addNewColumns` | Streaming ingest restarts on new columns and includes them on the next run |
| DLT / Lakeflow Declarative Pipelines | Built-in schema evolution with expectations |
| `MERGE INTO ... WITH SCHEMA EVOLUTION` | Upserts can introduce new target columns |

This demo deliberately picks a different posture: **bronze auto-absorbs, silver is governed**.

- **Bronze**: VARIANT is the most permissive form of auto-evolution — *every* new key is captured in `payload`, regardless of type or nesting, with zero data loss and full history. Nothing to configure, nothing to break.
- **Silver**: the `known_payload_keys` allow-list is the explicit contract. A new key in the API doesn't become a silver column until someone updates the list (notebook 05 step 1).
- **The alert is the bridge**: drift surfaces immediately via the DBSQL Alert, so "I didn't notice" never happens — but the response is a deliberate human decision, not an auto-merge.

The tradeoff:

| | Auto-evolve silver | Allow-list-gated silver (this demo) |
|---|---|---|
| New API key shows up in silver | Automatic, same day | Only after the allow-list is updated |
| Risk of silent contract changes downstream | Real — a dashboard suddenly has a new column | None — gold/dashboards only see what was reviewed |
| Lag between API change and silver coverage | None | One PR / notebook run (minutes to hours) |
| Best when… | Schema is owned end-to-end by one team, downstream is forgiving | Schema crosses team boundaries, downstream consumers expect stability |

If your customer prefers fully automatic, the change is small: swap the explicit `selectExpr(...)` in notebook 05 step 2 for a `payload:*` projection (or Auto Loader with `addNewColumns`), drop the allow-list, and keep the LHM monitor + Job alert as your safety net.

## Files

```
hockey-schema-monitoring/
├── README.md
├── DEMO.md                                # click-by-click UI walkthrough
├── requirements.txt
├── .env.example
├── 00_setup.ipynb
├── 01_bronze_variant_v1.ipynb
├── 02_silver_projection.ipynb
├── 03_drift_detector_and_monitoring.ipynb
├── 04_simulate_api_v2.ipynb
├── 05_schema_evolution.ipynb
├── alerts/
│   └── drift_alert.sql                    # paste into DBSQL Alerts UI
├── jobs/
│   └── strict_silver_job.json             # job config with email_notifications
└── Hockey — unknown payload keys.dbalert.json   # exported DBSQL alert config (Sidebar → Alerts → Import)
```

## Notes

- **No `MERGE`** — Databricks Connect (Spark Connect) doesn't support it. We use `INSERT INTO` / `saveAsTable(mode="append" | "overwrite")`.
- **VARIANT** requires DBR 15.3+ and a matching `databricks-connect` pin.
- **Lakehouse Monitoring** is created via `WorkspaceClient.lakehouse_monitors` (SDK). The monitor dashboard is generated by Databricks on first refresh.
