# basketball-reference-waf

An end-to-end Databricks demo: ingest NBA data from **Basketball Reference**, run it through a
**bronze → silver → gold** medallion ("WAF") pipeline, and train a simple ML model that
predicts the **home team's win probability** for each game — then register it to Unity
Catalog and score a held-out season.

It's the basketball cousin of the `hockey-xg-mlflow` demo: a calibrated probability model
("will the home team win, and how confident are we?") that's intuitive even if you don't
follow the sport.

> **Intended use:** this is an *architecture & MLOps* demo — how to ingest, govern, model,
> and serve sports data on Databricks. It is **not** a production prediction or betting
> system: it deliberately uses only team-form features (no injuries, player tracking, or
> strength-of-schedule adjustment), so read the accuracy as "credible demo," not "an edge."

## TL;DR

- **9 notebooks**, run `00` → `08` in order.
- Ingests **team season game logs** (one page per team-season) → ~90 web requests for 3
  seasons, *not* the ~530 a per-day scrape would need (see the rate-limit note below).
- Computes the **Four Factors** (shooting, turnovers, rebounding, free throws) — the
  box-score metrics most correlated with winning.
- Trains 3 models (Logistic Regression / Random Forest / XGBoost) with **MLflow**, registers
  the champion to **Unity Catalog** (`@champion` / `@challenger` aliases), and writes
  predictions back to a gold table.

## Architecture

```
Basketball Reference                Unity Catalog
  team game logs                    ┌─────────────────────────────────────────────┐
        │            01 ingest      │  _bronze.gamelog_raw        (VARIANT)         │
        └──────────────────────────▶│        │ 02 Auto Loader                       │
                                    │        ▼                                      │
                                    │  _silver.team_game_box  +  _silver.games      │
                                    │        │ 03  (Four Factors, MD5 keys, RELY/CHK)│
                                    │        ▼                                      │
                                    │  _gold.dim_team / dim_date /                  │
                                    │        fact_games / fact_team_game   04        │
                                    │        ▼                                      │
                                    │  _gold.game_features    05 (leakage-safe)     │
                                    │        ▼                                      │
                                    │  MLflow runs → UC model  06–07               │
                                    │        ▼  @champion                           │
                                    │  _gold.game_predictions 08                    │
                                    └─────────────────────────────────────────────┘
```

## ⚠️ Basketball Reference rate limits

Basketball Reference (sports-reference.com) enforces **~20 requests/minute** and will **IP-block
you for ~1 hour** (HTTP 429 with a `Retry-After` header) if you exceed it. This demo is
designed around that:

- It scrapes **team season game-log pages** (`/teams/{ABBR}/{year}/gamelog/`). Each page
  returns *every* game's full box score for that team **and** its opponent, so the whole demo
  is ~30 teams × N seasons ≈ **90 requests** total.
- It throttles to `NBA_SCRAPE_THROTTLE_SECONDS` (default 5s ≈ 12 req/min), honors
  `Retry-After`, and **caches every file in the landing Volume** so re-runs are instant and
  resumable.

Do not lower the throttle below ~3s, and avoid hammering — if you get a 429, just wait it out.

## Data source & licensing

Data is scraped from [Basketball Reference](https://www.basketball-reference.com/)
(Sports Reference LLC), whose **Terms of Use restrict automated scraping and redistribution**.
So:

- Fine for an **internal** Databricks demo against public, aggregate stats.
- **Do not redistribute** the scraped data or hand the raw tables to a customer as a
  deliverable, and don't publish them.
- For a real customer engagement, point notebook `01` at the **customer's own data** or a
  **licensed feed** (NBA Stats API, Sportradar, Genius Sports, etc.). The rest of the
  pipeline is source-agnostic — only the ingest notebook changes.
- Keep the polite throttle; treat the source's rate limits as a hard constraint.

## Data model

| Layer | Table | Grain |
|-------|-------|-------|
| bronze | `gamelog_raw` | one row per scraped team-season file (raw VARIANT array) |
| silver | `team_game_box` | one row per **team per game** (typed, Four Factors + ratings) |
| silver | `games` | one row per **game** (home perspective, `home_win` label) |
| gold | `dim_team`, `dim_date` | dimensions |
| gold | `fact_games`, `fact_team_game` | facts (star schema, RELY PK/FK) |
| gold | `game_features` | leakage-safe pre-game features (label `home_win`) |
| gold | `game_predictions` | champion model's scored holdout season |
| gold | `home_win_classifier` | the registered UC model (`@champion` / `@challenger`) |

## Prerequisites

- A Databricks workspace with Unity Catalog and **serverless** compute.
- Python 3.10+ with the version of `databricks-connect` in `requirements.txt` matching the
  workspace DBR.
- Outbound internet from where you run the notebooks (the scrape runs locally via Databricks
  Connect).

## Setup

```bash
cd basketball-reference-waf
pip install -r requirements.txt        # into your existing env is fine
cp .env.example .env                    # then fill in DATABRICKS_HOST / DATABRICKS_TOKEN
```

Run the notebooks `00` → `08` in order (each depends on the previous one's tables).

## Configuration (`.env`)

| Variable | Meaning |
|----------|---------|
| `DATABRICKS_HOST` / `DATABRICKS_TOKEN` | Workspace + PAT |
| `DATABRICKS_CLUSTER_ID` | Leave blank for serverless |
| `UC_CATALOG` / `UC_SCHEMA` | Target catalog and base schema (`_bronze`/`_silver`/`_gold` are derived) |
| `NBA_SEASONS` | Season-end years to ingest, comma-separated (the 2024-25 season is `2025`) |
| `NBA_HOLDOUT_SEASON` | Season held out for honest evaluation (registered model is judged on it) |
| `NBA_REGULAR_SEASON_ONLY` | Train on regular-season games only (playoffs still land in the medallion tables) |
| `NBA_SCRAPE_THROTTLE_SECONDS` | Seconds between web requests (≥5 recommended) |
| `NBA_MAX_TEAMS` | Optional — cap teams scraped per season for a fast smoke run |
| `MLFLOW_EXPERIMENT_NAME` | Experiment path under `/Users/<you>/...` |
| `MODEL_NAME` | Registered model name (created in the `_gold` schema) |

## Notebook flow

| # | Notebook | Does |
|---|----------|------|
| 00 | `00_verify_connection` | Serverless connect; create catalog, 3 schemas, landing Volume, MLflow experiment |
| 01 | `01_ingest_basketball_reference` | Scrape team game-logs → raw JSON in the Volume (throttled, idempotent) |
| 02 | `02_bronze_autoloader` | Auto Loader → `gamelog_raw` (VARIANT) |
| 03 | `03_silver_games_team_box` | Type + dedupe; compute Four Factors; `games` + `team_game_box`; RELY/CHECK |
| 04 | `04_gold_star_schema` | `dim_team`, `dim_date`, `fact_games`, `fact_team_game`, serving views |
| 05 | `05_build_features` | Leakage-safe season-to-date features → `game_features` |
| 06 | `06_train_with_mlflow` | Train 3 models; log params/metrics/ROC/calibration to MLflow |
| 07 | `07_evaluate_and_register` | Score on held-out season; register champion/challenger to UC |
| 08 | `08_batch_inference` | Score the holdout season via `@champion`; write `game_predictions` |

## The model

- **Target:** `home_win` (did the home team win?).
- **Features (difference, home − away):** win %, average margin, net rating, the four
  offensive Four Factors, the four defensive Four Factors, and rest-days — all computed
  **season-to-date and strictly before each game** (window frame ends `1 PRECEDING`, so a
  game's result can never leak into its own features).
- **Honest evaluation:** the most recent season is held out entirely; the champion is the
  model with the best hold-out log-loss, and must beat the **home-court baseline** (just
  always picking the home team, ~54–58% in these seasons).

### Results (3 seasons: 2022-23 → 2024-25)

Ingested 3,940 games (1,230 regular-season per year + playoffs); 3,222 games modeled after
the 10-game warm-up filter. Champion = **Logistic Regression** (best hold-out log-loss),
evaluated on the unseen **2024-25** season:

| Metric | Champion | Home-court baseline |
|--------|----------|---------------------|
| Accuracy | **0.658** | 0.542 |
| Log-loss | 0.606 | — |
| ROC-AUC | 0.725 | — |

That's **+11.5 points** over always picking the home team, and the predictions are
**well-calibrated** — games the model calls ~75% win ~72% of the time, ~92% calls win ~93%,
etc. (~65–67% accuracy is near the practical ceiling for pre-game NBA prediction.) Your exact
numbers will vary as seasons/data change.

## Key implementation details

- **VARIANT bronze + schema-on-read** — land the raw gamelog rows untouched; select/type only
  what's needed in silver.
- **`INSERT OVERWRITE` everywhere** — MERGE isn't supported on Spark Connect; full-refresh
  rebuilds are idempotent and stateless.
- **MD5 surrogate keys** — both teams in a game share the same `game_sk`, so the two box-score
  rows join cleanly; `team_game_sk` is unique per team-game.
- **RELY PK/FK + CHECK** — optimizer/ERD hints plus enforced data-quality guards.
- **Liquid clustering** `CLUSTER BY (season, game_date)` on the facts.
- **Idempotent, resumable ingest** — already-landed files are skipped, so a re-run only
  fetches what's missing.

## Re-run / reset

- Re-running any notebook is safe (full-refresh writes).
- To force a fresh scrape, delete the `team_gamelog/` folder under the bronze Volume.
- To drop everything: `DROP SCHEMA <catalog>.<schema>_{bronze,silver,gold} CASCADE`.

## Troubleshooting

| Symptom | Fix |
|---------|-----|
| `429 Too Many Requests` during ingest | You hit the rate limit. Wait out the `Retry-After`, raise `NBA_SCRAPE_THROTTLE_SECONDS`, then re-run (it resumes from the Volume cache). |
| Silver columns are null | Inspect the raw fields with the peek cell in notebook 01/02 and confirm the `data-stat` names used in notebook 03. |
| `MERGE not supported` | Expected on Spark Connect — this demo uses `INSERT OVERWRITE` only. |
| Model barely beats baseline | NBA home-court advantage is strong and games are noisy; ~63–67% accuracy is a realistic ceiling for pre-game features. |
