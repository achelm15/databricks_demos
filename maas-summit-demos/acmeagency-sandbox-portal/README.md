# Team 8 — MAAS Summit: Multi-Tenant Self-Serve Reporting on Lakebase

A Databricks App that demonstrates positioning **Lakebase** for a real industry use case: an ad agency's self-serve reporting portal for its advertiser clients.

Three Lakebase edge features land in this demo:
1. **Reverse sync** — gold reporting tables sync from Unity Catalog into Lakebase Postgres, queried directly by the app
2. **Scale-to-zero** — cost panel quantifies savings from idle-tenant economics
3. **Branching** — "Onboard advertiser" spins up a Lakebase branch in seconds

See [`BRIEF.md`](./BRIEF.md) for the full workshop scope.

---

## Quick start

### 1. Set environment

```bash
cp .env.example .env
# fill in DATABRICKS_HOST, DATABRICKS_TOKEN (or use a profile), CATALOG, SCHEMA, LAKEBASE_INSTANCE
```

The repo assumes `~/miniconda3/envs/demo-env`. Activate:

```bash
conda activate demo-env
```

### 2. Run notebooks in order

Open in Databricks workspace (or run locally via Databricks Connect):

```bash
notebooks/00_setup.ipynb              # creates catalog/schema, gold tables, synthetic data
notebooks/01_provision_lakebase.ipynb # creates Lakebase instance, synced tables, RLS policy
notebooks/02_demo_branching.ipynb     # walkthrough of branch lifecycle
```

### 3. Local frontend dev (optional)

```bash
cd frontend && npm install && npm run dev
# in a separate shell:
cd backend && uvicorn main:app --reload --port 8000
```

### 4. Deploy as a Databricks App

```bash
bash scripts/deploy.sh
```

This syncs the source dir to `/Workspace/Users/<you>/maas-summit-team8` and creates/updates the Databricks App named `maas-summit-team8`. Open the URL it prints to test live.

The frontend is **no-build** — React + Recharts load from esm.sh via an importmap, so there is no `npm install`, no Vite, no `frontend/dist/`. The FastAPI backend serves `frontend/index.html`, `frontend/app.js`, and `frontend/styles.css` directly. This matters because in many Databricks workspaces the public npm registry is blocked.

**Note (e2-demo-field-eng workspace):** at the time of this writeup the workspace is at its 300-app quota. Deploy will fail with `reached the maximum limit of 300 apps`. The team should deploy this app to whatever workspace they bring to the workshop. The deploy script is unchanged; only the target workspace differs.

#### Local dev (no App deploy)

The app runs locally end-to-end against the live Lakebase instance. Useful for iteration during Day-2 native-tooling builds:

```bash
LOCAL_DEV_EMAIL=$(databricks current-user me -o json | jq -r .userName) \
  ~/miniconda3/envs/demo-env/bin/uvicorn backend.main:app --reload --port 8765
# open http://127.0.0.1:8765/
```

`LOCAL_DEV_EMAIL` tells the middleware to use your databricks-cli OAuth token as the Lakebase password (the Apps proxy normally does this for you). Switch tenants with the "VIEW AS" selector in the top-right.

---

## Architecture

```
React (Vite)  -->  FastAPI  -->  asyncpg pool  -->  Lakebase Postgres
                                                          ^
                                                          | reverse-synced
                                  UC gold tables  --------+
```

Auth: Databricks Apps proxy injects `X-Forwarded-Email` and `x-forwarded-access-token`. Backend middleware uses the **user's** token (not the SP's) to authenticate with Lakebase — the SP token lacks Lakebase security labels.

Tenant isolation: Single Lakebase instance, RLS policy keyed on `advertiser_id` from JWT email mapping.

Branching: `POST /api/branches` calls `WorkspaceClient.database.create_database_instance(parent_instance_ref=...)` to spawn a branch.

---

## Files of interest

| Path | What it does |
|------|--------------|
| `notebooks/00_setup.ipynb` | Catalog, schema, 4 gold tables, 9 advertisers, ~50 campaigns, 84 days of daily perf |
| `notebooks/01_provision_lakebase.ipynb` | Lakebase instance + synced tables + RLS |
| `notebooks/02_demo_branching.ipynb` | Create a branch, point a connection at it, tear it down |
| `backend/db.py` | asyncpg pool + OAuth user-token refresh middleware |
| `backend/routers/branches.py` | Lakebase branch lifecycle endpoints |
| `backend/routers/cost.py` | Scale-to-zero savings calculation |
| `frontend/src/components/OnboardModal.tsx` | The "wow" branching moment |
| `frontend/src/components/CostPanel.tsx` | Idle savings panel |

---

## Workshop context

This was built Day-1 of the 2026 MAAS SA Summit Workshop using external coding agents (Claude Code). Day 2 the team rebuilds the same target using Databricks-native agents (Genie Code, Databricks Assistant, in-workspace AI) and logs friction points back to PM. See [`BRIEF.md`](./BRIEF.md) §6 for feedback capture format.
