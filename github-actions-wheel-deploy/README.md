# Deploying Python Wheels to Databricks via GitHub Actions

## The Problem

Your team maintains internal Python packages in GitHub (shared transforms, utilities,
ML feature logic, etc.). Today, getting a new version onto Databricks involves manual
steps — building locally, uploading to DBFS or a Volume, restarting clusters. That's
error-prone and doesn't scale across environments.

This demo shows how to automate the full workflow: **push code → build wheel → deploy
to Databricks** — all through GitHub Actions.

## How It Works

```
┌──────────────┐     ┌──────────────────┐     ┌────────────────────────┐
│  Developer   │────→│  GitHub Actions   │────→│  Databricks Workspace  │
│  pushes to   │     │                  │     │                        │
│  main branch │     │  1. Build wheel  │     │  Unity Catalog Volume  │
│              │     │  2. Upload to    │────→│  /Volumes/.../wheels/  │
│              │     │     Databricks   │     │                        │
└──────────────┘     └──────────────────┘     └────────────────────────┘
```

### The Pipeline

1. **Trigger**: Developer pushes to `main` (or manually triggers from GitHub UI)
2. **Build job**: Checks out code, builds the `.whl` file using `python -m build`
3. **Deploy job**: Downloads the wheel artifact, uses the Databricks CLI to upload it
   to a Unity Catalog Volume (or DBFS)
4. **Consume**: Notebooks and jobs reference the wheel via `%pip install` or cluster
   init scripts

## What's in This Demo

```
github-actions-wheel-deploy/
├── .github/workflows/
│   └── build-and-deploy.yml    ← GitHub Actions workflow
├── astros_utils/               ← Sample Python package
│   ├── pyproject.toml
│   └── astros_utils/
│       ├── __init__.py
│       └── transforms.py       ← Sample PySpark transforms
├── .env.example
└── README.md
```

## Setup (One-Time)

### 1. Add GitHub Secrets

In your GitHub repo, go to **Settings → Secrets and variables → Actions** and add:

| Secret | Value |
|--------|-------|
| `DATABRICKS_HOST` | `https://your-workspace.cloud.databricks.com` |
| `DATABRICKS_TOKEN` | A personal access token or service principal token |

### 2. Create the target Volume (or DBFS path)

```sql
-- Run in a Databricks notebook or SQL editor
CREATE VOLUME IF NOT EXISTS astros_catalog.shared.wheels;
```

### 3. Configure the workflow

Edit `.github/workflows/build-and-deploy.yml` and set:
- `DEPLOY_PATH` — where the wheel lands (UC Volume path or DBFS path)
- `PACKAGE_DIR` — the directory containing `pyproject.toml`

## Using the Deployed Wheel

Once the wheel is in a Volume, reference it from notebooks or jobs:

```python
# In a Databricks notebook
%pip install /Volumes/astros_catalog/shared/wheels/astros_utils-0.1.0-py3-none-any.whl

from astros_utils.transforms import add_game_date_parts, calculate_batting_avg
```

Or install it in a cluster init script so it's always available:

```bash
#!/bin/bash
pip install /Volumes/astros_catalog/shared/wheels/astros_utils-0.1.0-py3-none-any.whl
```

Or attach it as a cluster library via the UI:
**Compute → your cluster → Libraries → Install new → Upload → select from Volume**

## Deployment Targets: UC Volume vs. DBFS

| | **Unity Catalog Volume** (recommended) | **DBFS** (legacy) |
|---|---|---|
| Path format | `/Volumes/catalog/schema/volume/` | `dbfs:/path/to/libs/` |
| Governance | Full UC permissions, audit log | Workspace-level ACLs only |
| Cross-workspace | Accessible from any workspace with catalog access | Single workspace |
| Cleanup | Standard file management | Manual |

**Use UC Volumes** unless you're on a workspace that doesn't have Unity Catalog enabled yet.

## Versioning Strategy

The workflow in this demo uses `--overwrite` to replace the wheel on every push.
For production, consider one of these patterns:

**Option A: Version in the filename (recommended)**
```
/Volumes/.../wheels/astros_utils-0.1.0-py3-none-any.whl
/Volumes/.../wheels/astros_utils-0.2.0-py3-none-any.whl
```
Bump the version in `pyproject.toml` on each release. Old versions stay available
for rollback. Notebooks pin to a specific version.

**Option B: Latest + versioned**
```
/Volumes/.../wheels/astros_utils-latest.whl       ← overwritten each push
/Volumes/.../wheels/astros_utils-0.1.0.whl        ← archived
```
Dev notebooks use `latest`, production jobs pin to a version.

**Option C: Git tag triggers**
Change the workflow trigger from `push` to `release`, so wheels are only built
and deployed when you create a GitHub release/tag. Cleanest for production.

## Extending This

### Multiple packages
If your org has several internal packages, you can either:
- Use a **monorepo** with one workflow that builds multiple wheels (matrix strategy)
- Use **separate repos** each with their own copy of this workflow

### Multi-environment deploy (dev → staging → prod)
Add environment-specific secrets and a matrix strategy:
```yaml
strategy:
  matrix:
    env: [dev, staging, prod]
```
Each environment has its own `DATABRICKS_HOST` / `DATABRICKS_TOKEN` secrets.

### Running tests before deploy
Add a `test` job between `build` and `deploy`:
```yaml
test:
  needs: build
  runs-on: ubuntu-latest
  steps:
    - uses: actions/checkout@v4
    - run: pip install pytest
    - run: pip install dist/*.whl
    - run: pytest tests/
```

### Alternative: Databricks Asset Bundles (DABs)
If you're deploying notebooks, jobs, and libraries together as a unit, consider
[Databricks Asset Bundles](https://docs.databricks.com/en/dev-tools/bundles/index.html)
which can bundle wheels alongside job definitions in a single `databricks.yml`.

## Data Disclaimer

The sample `astros_utils` package contains placeholder PySpark functions for demonstration
purposes only. It is not affiliated with any real organization.
