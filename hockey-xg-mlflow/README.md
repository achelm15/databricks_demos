# Hockey xG — MLOps with MLflow on Databricks

A self-contained, hockey-themed walkthrough of the MLflow + Unity Catalog story on
Databricks. Starts from **synthetic shot data** (no API or credentials needed),
engineers features, trains three competing **expected-goals (xG)** models, registers
the winner to the **UC Model Registry**, deploys it to **Model Serving**, and turns
on **Lakehouse Monitoring** so you can watch drift in action.

Designed as a ~60-minute customer-facing demo of "MLOps on Databricks" — works
both from a laptop via **Databricks Connect (serverless)** and from a Databricks
workspace Git Folder.

## What it shows

| Topic | Where |
|-------|-------|
| MLflow tracking — params, metrics, custom artifacts (ROC, calibration, feature importance) | `03_train_with_mlflow` |
| Run comparison + best-run selection | `03`, `04` |
| Model signature + input example + custom pyfunc wrapper | `03` |
| Holdout evaluation (log-loss / Brier / ROC AUC / PR AUC) | `04` |
| **UC Model Registry** + `@champion` / `@challenger` aliases | `04` |
| Loading models by alias for inference | `05`, `06` |
| Data + model lineage in UC | `05` |
| **Model Serving** endpoint (scale-to-zero, CPU) | `06` |
| Inference table on the endpoint | `06` |
| **Lakehouse Monitoring** + drift simulation | `07` |

## Architecture

```
┌────────────────────────────────────────────────────────────────────────────┐
│  01_generate_synthetic_shots  →  shots_raw  (Delta)                        │
│  ~50k shots, 32 teams, 1 season. Hidden ground-truth P(goal) function so   │
│  models can actually learn signal.                                          │
└──────────────────────────────────┬─────────────────────────────────────────┘
                                   ▼
┌────────────────────────────────────────────────────────────────────────────┐
│  02_features_and_eda  →  shots_features  (Delta)                            │
│  distance / angle / shot_type / strength / rebound / rush / period          │
└──────────────────────────────────┬─────────────────────────────────────────┘
                                   ▼
┌────────────────────────────────────────────────────────────────────────────┐
│  03_train_with_mlflow                                                       │
│  LogisticRegression  /  RandomForest  /  XGBoost                            │
│  Three runs in one experiment — autolog + signature + ROC / calibration    │
└──────────────────────────────────┬─────────────────────────────────────────┘
                                   ▼
┌────────────────────────────────────────────────────────────────────────────┐
│  04_evaluate_and_register                                                   │
│  mlflow.evaluate → pick best → register to UC → @champion / @challenger    │
└──────────────────────────────────┬─────────────────────────────────────────┘
                                   ▼
              ┌────────────────────┴────────────────────┐
              ▼                                         ▼
┌────────────────────────────┐         ┌────────────────────────────────────┐
│  05_batch_inference        │         │  06_serving_endpoint               │
│  models:/...@champion      │         │  REST endpoint + inference table   │
│  shot_predictions (Delta)  │         │                                    │
└──────────────┬─────────────┘         └────────────────────────────────────┘
               ▼
┌────────────────────────────────────────────────────────────────────────────┐
│  07_monitoring_and_drift                                                    │
│  Lakehouse Monitor on shot_predictions + drifted batch → see metrics shift │
└────────────────────────────────────────────────────────────────────────────┘
```

## Notebook reference

| # | Notebook | Purpose |
|---|----------|---------|
| 00 | `00_setup.ipynb` | Verify Spark + UC; create catalog/schema + MLflow experiment |
| 01 | `01_generate_synthetic_shots.ipynb` | Generate `shots_raw` (~50k shots, realistic distributions) |
| 02 | `02_features_and_eda.ipynb` | Build `shots_features`; quick EDA (shot map, goal rate by zone/type) |
| 03 | `03_train_with_mlflow.ipynb` | Three competing xG models — full MLflow tracking |
| 04 | `04_evaluate_and_register.ipynb` | Evaluate, register to UC, set aliases |
| 05 | `05_batch_inference.ipynb` | Load by alias, score holdout → `shot_predictions` |
| 06 | `06_serving_endpoint.ipynb` | Deploy Model Serving endpoint + inference table |
| 07 | `07_monitoring_and_drift.ipynb` | Lakehouse Monitor + drift simulation |

Run them in order.

## Setup

```bash
cd hockey-xg-mlflow
python -m venv .venv
source .venv/bin/activate            # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env                  # fill in credentials
```

> `databricks-connect` bundles PySpark — do **not** install standalone `pyspark`
> alongside it.

Authenticate via the Databricks CLI (preferred):

```bash
databricks auth login --host https://e2-demo-field-eng.cloud.databricks.com
```

Then open the notebooks in your editor of choice and run them in order.

## Running in a Databricks workspace Git Folder

Clone the repo as a Git Folder, attach to a serverless or DBR 15+ ML runtime, and
run the notebooks from there. Credentials resolve from notebook context — no
`.env` needed.

## Cleanup

Each notebook is idempotent (`CREATE OR REPLACE`, `INSERT OVERWRITE`). To remove
everything:

```sql
DROP SCHEMA IF EXISTS alexander_booth.hockey_xg_mlflow CASCADE;
```

And in the Serving UI, delete the endpoint named in `SERVING_ENDPOINT_NAME`.

## Notes

- Targets **Serverless** by default. `DatabricksSession.builder.serverless().getOrCreate()`.
- `MERGE` is not supported via Spark Connect — the notebooks use `INSERT OVERWRITE`
  / `saveAsTable(mode="overwrite")` instead.
- Synthetic data only — numbers are not real hockey, but the modeling pipeline is
  identical to what you'd run on real event data.
