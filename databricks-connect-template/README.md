# Databricks Connect — Starter Template

Run Databricks notebooks locally in VS Code or Cursor, with compute and data living in Databricks.

---

## How it works

Your code runs locally. Spark plans are sent to a remote Databricks cluster via **Databricks Connect**. Results stream back to your IDE. No need to clone this repo into Databricks.

```
VS Code / Cursor
    │  Databricks Connect (gRPC)
    ▼
Databricks Cluster  ──►  Unity Catalog / Delta Lake
```

---

## Setup

### 1. Install dependencies

Create a virtual environment (recommended) then install:

```bash
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

> `databricks-connect` bundles PySpark. Do **not** install `pyspark` separately — they conflict.

### 2. Authenticate

**Option A — Databricks CLI (recommended, nothing to hardcode):**

```bash
pip install databricks-cli
databricks configure          # enter host + token when prompted
```

This writes `~/.databrickscfg`. Databricks Connect picks it up automatically.

**Option B — Environment variables:**

```bash
cp .env.example .env
# Edit .env with your host, token, and cluster ID
```

`.env` is gitignored. Never commit real credentials.

### 3. Point to a cluster

Your cluster must run **DBR 13.3+** (required for Databricks Connect v2).

Set `DATABRICKS_CLUSTER_ID` in `.env` or export it:

```bash
export DATABRICKS_CLUSTER_ID=<your-cluster-id>
```

Or set it once in `~/.databrickscfg`:

```ini
[DEFAULT]
host  = https://your-workspace.cloud.databricks.com
token = dapiXXXXXXXX
cluster_id = 0000-000000-xxxxxxxx
```

### 4. Select the kernel in VS Code / Cursor

Open a notebook → click the kernel picker (top right) → select your `.venv` Python interpreter.

---

## Notebooks

| Notebook | What it does |
|---|---|
| [00_verify_connection.ipynb](00_verify_connection.ipynb) | Confirms auth + cluster connectivity |
| [01_explore_catalog.ipynb](01_explore_catalog.ipynb) | Browses Unity Catalog via Spark SQL + Databricks SDK |

---

## Key packages

| Package | Purpose |
|---|---|
| `databricks-connect` | Local → remote Spark execution |
| `databricks-sdk` | Workspace REST API (clusters, jobs, catalogs, etc.) |
| `python-dotenv` | Load `.env` for local credential overrides |

---

## Tips

- **Restart cluster?** Just re-run `DatabricksSession.builder.getOrCreate()` — it reconnects.
- **Delta tables** work out of the box; no extra config needed.
- **MLflow** tracking server is your Databricks workspace by default — logs go there automatically.
- **Serverless compute** is supported in DBR 14.3+ — set `cluster_id` to a serverless warehouse ID.
