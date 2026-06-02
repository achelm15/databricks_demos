# Demo run sheet — basketball-reference-waf

A ~15–20 min live walkthrough for a sports/analytics audience. The story: **real data →
governed medallion → analytics → MLflow → UC-registered, calibrated model → predictions**,
all on Databricks.

## Before the meeting (pre-flight)

- **Pre-run all notebooks** so everything is cached and instant. Do **not** scrape live in
  front of the audience (rate limits) — `01` reads from the Volume cache once landed.
  - Fast option: set `NBA_MAX_TEAMS=6` in `.env` for a quick partial run.
- Open these browser tabs in the workspace, ready to flip to:
  1. **Catalog Explorer** → `…_silver.team_game_box` (column comments + Four Factors) and
     `…_gold.fact_games` (the **ERD** from RELY keys, under "Relationships").
  2. **MLflow experiment** `…/basketball-reference-waf` → the 3 runs, sorted by `val_log_loss`.
  3. **Registered model** `…_gold.home_win_classifier` → the `@champion` / `@challenger` aliases.
  4. Notebook `08` output (calibration table + "biggest upsets").
- One-liner to open with: *"This is how you'd ingest, govern, and model sports data on
  Databricks — end to end, in one platform."*

## The walkthrough (what to click + say)

| Notebook | Show | Say |
|----------|------|-----|
| **00** | the 3 schemas + Volume + MLflow experiment created | "Serverless — no cluster to manage. Bronze/silver/gold separation from line one." |
| **01** | the ingest summary (90 files, 0 failures) | "One page per team-season — rate-limit-friendly and idempotent; re-runs hit the cache." |
| **02** | `gamelog_raw` VARIANT table | "**Schema-on-read** — we land the raw payload untouched. When the source changed its HTML, it was a one-line fix downstream, not a re-scrape." |
| **03** | `team_game_box` + the **Four Factors** | "Now it's typed and deduped with MD5 keys, plus the **Four Factors** — the box-score metrics most correlated with winning. RELY keys + CHECK constraints enforce quality." |
| **04** | Catalog Explorer → `fact_games` **Relationships/ERD**; the net-rating leaderboard | "Star schema. The ERD is generated from the keys. Sanity check: top net-rating team is OKC — the actual #1 — so the data's right." |
| **05** | `game_features` + the leakage guard (0 violations) | "Every feature uses only games **before** tip-off — no leakage. This is where you'd add injuries, travel, strength-of-schedule." |
| **06** | the 3 MLflow runs + **calibration curves** | "Three models, fully tracked — params, metrics, ROC, and **calibration**. We care that 70% really means 70%." |
| **07** | the registered model + `@champion`/`@challenger` | "Best model on a **held-out season** is registered to Unity Catalog with aliases — governed like any other data asset, ready to promote/roll back." |
| **08** | accuracy vs baseline, the calibration table, biggest upsets | "**65.8% vs a 54.2% home-court baseline**, and well-calibrated. Predictions land back in a governed gold table with lineage." |

## The three "money" moments

1. **Calibration** (06/08) — "It's not just ranking games; the probabilities are trustworthy."
2. **Governance/lineage** (Catalog Explorer + UC model) — "Data, features, and the model are
   all governed and lineage-tracked in one place."
3. **Champion/challenger + held-out eval** (07) — "Honest evaluation and safe model promotion."

## Likely questions (and answers)

- *"Why no injuries / Vegas line / strength-of-schedule?"* — Intentionally simple to show the
  platform. All are easy adds in notebook `05` (features) → retrain `06` → promote `07`.
- *"Is this production-grade prediction?"* — No — it's an architecture/MLOps demo. The point is
  the pipeline and governance; swap in richer data/features for production.
- *"Can we use our own data?"* — Yes. Only notebook `01` (ingest) is source-specific; point it
  at your feed and the rest is unchanged.
- *"Can we have the data?"* — Note the Basketball Reference licensing (see README): don't
  redistribute the scraped data. For a real engagement we'd use your licensed data.

## Reset between runs

- Re-running any notebook is safe (full-refresh writes).
- Fresh scrape: delete the `team_gamelog/` folder under the bronze Volume.
- Tear down: `DROP SCHEMA <catalog>.<schema>_{bronze,silver,gold} CASCADE`.
