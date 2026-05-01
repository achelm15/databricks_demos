# Sanity-check pipeline without SportLogiq credentials

A self-contained integration harness that fakes the SportLogiq response shapes,
writes them to the same UC Volume paths the real ingest would write to, and lets
you run the rest of the pipeline (`02_bronze_autoloader` → `07_create_genie_space`)
end-to-end against synthetic data.

**Use case:** prove the bronze/silver/gold/dashboard/Genie code is structurally
sound before you have API credentials in hand. Not for customer demos — the
numbers are made up. Just engineering confidence.

## What it does

`generate_fake_data.ipynb` creates a small, deterministic, schema-shaped corpus:

| Layer | Generated |
|-------|-----------|
| Reference | 1 competition (NHL), 8 teams, 8 venues, 50 players, 4 metric-topic scope files (2 topics each), 1 team-records file |
| Per-game (×5 games) | game detail, roster, compiled events (~30/game), full events, shift events, player TOI, per-topic metrics |
| Season metrics | 4 scopes × 2 topics each |

Files land at the **exact same Volume paths** notebook 01 would write to:

```
/Volumes/{UC_CATALOG}/{UC_SCHEMA}_bronze/raw_data/
  reference/...
  games/{game_id}/...
  season_metrics/{scope}/{topic_id}.json
```

## Workflow

You **skip** notebooks 00 and 01 (both need real SportLogiq creds). You run:

1. **Configure `.env`** — fill in `DATABRICKS_HOST`, `DATABRICKS_TOKEN`,
   `UC_CATALOG`, `UC_SCHEMA`, `SQL_WAREHOUSE_ID`. The SportLogiq creds can be
   bogus / blank — this notebook never calls the API.
2. **Run `tests/generate_fake_data.ipynb`** — creates schemas + Volume,
   generates ~150 JSON files, uploads them.
3. **Run `02_bronze_autoloader.ipynb`** — Auto Loader picks up the fake files
   and builds 16 VARIANT bronze tables.
4. **Run `03_silver_transformations.ipynb`** through **`07_create_genie_space.ipynb`** as normal.
5. (Optional) **Reset:** there's a cleanup cell at the end of `generate_fake_data.ipynb`
   that drops the schemas + Volume.

## What this proves vs. doesn't

**Proves:**
- VARIANT path syntax + `from_json` in silver line up with the file shapes
- MD5 surrogate keys are unique, PK/FK constraints apply cleanly
- Liquid clustering and `INSERT OVERWRITE` work
- Star-schema joins resolve, gold facts populate
- Lakeview dashboard widgets render
- Genie space loads without error

**Doesn't prove:**
- The real SportLogiq response shapes match these guesses 100% — when you get
  creds, run notebook 01 and watch Auto Loader's `_rescued` column. Anything
  that lands there is a field this harness didn't anticipate.
- Metric values are realistic (the fake values are uniform random — no Corsi
  vs. shooting-percentage signal).
- The dashboard heatmap / pie are visually meaningful — they'll *render*, but
  the shape is just synthetic noise.
