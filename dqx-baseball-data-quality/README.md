# DQX Baseball Data Quality

A standalone demo of the [Databricks Labs **DQX**](https://github.com/databrickslabs/dqx) data-quality framework, run locally via **Databricks Connect** (serverless) against synthetic baseball pitch-level data.

Four notebooks: profile → generate rules → apply checks → quarantine → metrics over time.

## What this demo shows

| DQX feature | Where |
|---|---|
| `DQProfiler` — auto-profile a DataFrame, get summary stats + per-column profiles | `02_profile_and_generate_rules` |
| `DQGenerator.generate_dq_rules` — turn profiles into candidate checks | `02_…` |
| YAML-defined checks (`is_not_null_and_not_empty`, `is_in_range`, `is_in_list`, `is_unique`, `sql_expression`) | `checks.yml` + `03_apply_checks_and_quarantine` |
| Python-defined checks (`DQRowRule`, `DQDatasetRule`, `regex_match`) | `03_…` |
| `DQEngine.validate_checks` — lint rules before running | `02_…`, `03_…` |
| `apply_checks_by_metadata` and `apply_checks_and_split` — tag or quarantine bad rows | `03_…` |
| `_errors` / `_warnings` result columns | `03_…`, `04_…` |
| Longitudinal `dq_results` table for dashboards / alerts | `04_dq_metrics_over_time` |

## How this differs from `mlb-gumbo-waf/06_reliability_dq`

`mlb-gumbo-waf` uses a **hand-rolled** SQL-predicate runner — fine for showing the *shape* of a DQ pipeline. This demo is purely about the **DQX library itself**: profiler, YAML config, Python rules, quarantine semantics, the `_errors`/`_warnings` result schema. No real APIs, no medallion pipeline — just DQX.

## Prerequisites

| | |
|---|---|
| **Databricks workspace** | Unity Catalog enabled, Serverless compute available |
| **Python** | 3.10+ |
| **DQX runtime support** | DBR 14.3 LTS+ (matches the `databricks-connect` pin in `requirements.txt`) |

## Setup

This demo runs in the shared `demo-env` conda env. The only package missing there
is `databricks-labs-dqx` itself (and its `databricks-labs-blueprint` dep).

If your network blocks PyPI (some corp setups have `127.0.0.1 pypi.org` in
`/etc/hosts`), pull the wheels straight from GitHub releases:

```bash
conda activate demo-env

# DQX 0.14.0 + blueprint 0.12.0
gh release download v0.14.0 -R databrickslabs/dqx       --pattern "*.whl" -D /tmp --clobber
gh release download v0.12.0 -R databrickslabs/blueprint --pattern "*.whl" -D /tmp --clobber

pip install --no-deps /tmp/databricks_labs_dqx-0.14.0-py3-none-any.whl \
                      /tmp/databricks_labs_blueprint-0.12.0-py3-none-any.whl

cp .env.example .env   # fill in DATABRICKS_HOST / TOKEN
```

The `databricks-sdk~=0.73` pin in DQX's wheel metadata is loose in practice — DQX
only needs `WorkspaceClient`, which works fine on the older `databricks-sdk 0.52`
already in `demo-env`.

If you have unrestricted PyPI access, just:

```bash
conda activate demo-env
pip install -r requirements.txt
```

## Configuration (`.env`)

| Variable | Required | Default | Notes |
|---|---|---|---|
| `DATABRICKS_HOST` | yes | — | `https://<workspace>.cloud.databricks.com` |
| `DATABRICKS_TOKEN` | yes | — | PAT or OAuth |
| `DATABRICKS_CLUSTER_ID` | no | _blank_ | leave blank for **Serverless** |
| `UC_CATALOG` | no | `alexander_booth` | catalog to create schemas in |
| `UC_SCHEMA` | no | `dqx_baseball` | base name; creates `_bronze` / `_silver` / `_quarantine` |
| `N_PITCHES` | no | `50000` | row count for synthetic dataset |
| `DIRTY_FRACTION` | no | `0.12` | fraction of rows with planted issues |
| `RANDOM_SEED` | no | `42` | for reproducibility |

## Notebook flow

| # | Notebook | What it does |
|---|---|---|
| 00 | `00_verify_connection` | Verify Databricks Connect + DQX import; create catalog/schemas |
| 01 | `01_generate_dirty_data` | Faker-built synthetic pitch table with planted quality issues → `*_bronze.pitches_raw` |
| 02 | `02_profile_and_generate_rules` | `DQProfiler` + `DQGenerator` → `checks.generated.yml` |
| 03 | `03_apply_checks_and_quarantine` | Apply YAML + Python checks → `*_silver.pitches` + `*_quarantine.pitches_quarantine` |
| 04 | `04_dq_metrics_over_time` | Aggregate failures into `*_silver.dq_results` for dashboards |

Run **00 → 01 → 02 → 03 → 04** in order.

## Synthetic data

`01_generate_dirty_data` creates ~50k rows of pitch-level data with these planted issues (~12% of rows):

- Null `pitcher_id` / `batter_id`
- Negative or > 130 mph `pitch_speed_mph`
- `inning > 20`
- `batting_avg` outside [0, 1]
- Bogus `pitch_type` codes (e.g. `XX`, `??`)
- Future `game_date`
- Duplicate `at_bat_id`s

Every planted issue maps to at least one rule in `checks.yml` so the rule-level breakdown in notebook 03 is interpretable.

## Files

```
dqx-baseball-data-quality/
├── README.md
├── requirements.txt
├── .env.example
├── checks.yml                      # hand-curated rules
├── checks.generated.yml            # written by notebook 02 (runtime artifact)
├── 00_verify_connection.ipynb
├── 01_generate_dirty_data.ipynb
├── 02_profile_and_generate_rules.ipynb
├── 03_apply_checks_and_quarantine.ipynb
└── 04_dq_metrics_over_time.ipynb
```

## Notes

- **No `MERGE`** — Databricks Connect (Spark Connect) doesn't support it. We use `INSERT OVERWRITE` / `saveAsTable(mode="overwrite")` everywhere.
- DQX is a pure-Python library, but `apply_checks_*` builds Spark plans that execute server-side — works fine through Databricks Connect.
- `DQProfiler` defaults to a 30% sample capped at 1,000 rows; tune via `DQProfiler.profile(df, opts={...})` if you need more.
