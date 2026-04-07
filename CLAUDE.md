# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Repository Overview

A collection of standalone Databricks demos showcasing data engineering, ML, streaming, and platform features. Each top-level directory is an independent demo with its own notebooks, dependencies, and README. There is no shared build system or monorepo tooling — demos are self-contained.

## Demo Patterns

Demos fall into two generations:

**Newer demos** (databricks-connect-template, delta-sharing-duckdb, ticketmaster-event-analytics, primary-keys-unique-constraints, streaming-demo, github-actions-wheel-deploy, unit-testing-pyspark, excel-dbr18x): Use `.env` + `python-dotenv` for credentials, `requirements.txt` for dependencies, `.env.example` as a template, and Jupyter notebooks (`.ipynb`) run locally via **Databricks Connect** (serverless).

**Older demos** (MLB GUMBO E2E, SparkML via Databricks Connect, Cohere Embedding Vector Search, etc.): Use a `config.py` with hardcoded workspace URIs/tokens. Some use plain `.py` files intended to run as Databricks notebooks.

## Common Setup for Newer Demos

```bash
cd <demo-directory>
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # fill in credentials
```

Run notebooks sequentially starting from `00_verify_connection.ipynb`.

`databricks-connect` bundles PySpark — do not install standalone `pyspark` alongside it.

## Running Tests

Only `unit-testing-pyspark/` has a test suite:

```bash
cd unit-testing-pyspark
source .venv/bin/activate
pytest tests/ -v
```

## Key Conventions

- Notebooks are numbered (`00_`, `01_`, ...) and must run in order — later notebooks depend on schemas/tables created by earlier ones
- Newer demos target **Serverless** compute by default (leave `DATABRICKS_CLUSTER_ID` blank)
- Unity Catalog is assumed: demos create catalogs, schemas, and tables in UC
- Bronze → Silver → Gold medallion architecture is used in multi-notebook pipelines (ticketmaster, streaming)
- `*config.py` is gitignored — older demos use this for credentials
- `.env` and `share_profile.json` are gitignored

## Databricks Connect Notes

- Demos use `DatabricksSession.builder.serverless().getOrCreate()` (or `.remote()` for classic clusters)
- `MERGE` is not supported via Databricks Connect (Spark Connect) — demos use `INSERT OVERWRITE` instead
- DBR version of `databricks-connect` in `requirements.txt` must match the workspace runtime version
