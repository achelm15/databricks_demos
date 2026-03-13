# Unit Testing PySpark — Field Demo

Learn how to write and run unit tests for PySpark transformations using **pytest**. Uses baseball performance data (batting averages, slugging, ERA) as the domain.

---

## Who Is This For?

Anyone who writes PySpark code and wants to:
- Understand what unit tests are and why they matter
- Learn how pytest works (from scratch — no prior testing experience needed)
- Test pure Python functions AND Spark DataFrame transformations
- Run tests locally, in notebooks, and in CI/CD

---

## What's Tested

`baseball_stats.py` contains two kinds of functions:

### Pure Python (no Spark)
| Function | What it computes |
|---|---|
| `batting_average()` | Hits / At-Bats |
| `slugging_percentage()` | Total Bases / At-Bats |
| `on_base_percentage()` | (H + BB + HBP) / (AB + BB + HBP + SF) |
| `ops()` | OBP + SLG |
| `era()` | (Earned Runs / Innings Pitched) * 9 |
| `whip()` | (Walks + Hits) / Innings Pitched |
| `classify_hitter()` | Tier label based on batting average |

### PySpark Transformations
| Function | What it does |
|---|---|
| `add_batting_average()` | Adds a `batting_avg` column to a DataFrame |
| `add_slugging_pct()` | Adds a `slugging_pct` column |
| `filter_qualified_batters()` | Filters to players with minimum at-bats |
| `top_n_by_stat()` | Returns top N rows by any stat column |
| `aggregate_team_stats()` | Groups and sums stats by team |

---

## Notebooks

| Notebook | What it covers |
|---|---|
| [00_what_are_unit_tests.ipynb](00_what_are_unit_tests.ipynb) | Concepts: what tests are, how pytest works, fixtures, Spark testing |
| [01_run_tests_locally.ipynb](01_run_tests_locally.ipynb) | Run the test suite from your local machine |
| [02_run_tests_in_notebook.ipynb](02_run_tests_in_notebook.ipynb) | Run tests inside a Databricks notebook |
| [03_explore_the_data.ipynb](03_explore_the_data.ipynb) | Use the tested functions on a larger dataset |

---

## Test Structure

```
tests/
├── conftest.py              ← Shared fixtures (SparkSession, sample DataFrames)
├── test_pure_python.py      ← 17 tests — no Spark needed, runs instantly
└── test_spark_transforms.py ← 14 tests — validates DataFrame transformations
```

### Key Concepts

- **conftest.py** — pytest auto-discovers this file. Fixtures defined here are available to all tests without importing.
- **`@pytest.fixture(scope="session")`** — creates the SparkSession once for the entire test run (not per-test).
- **`spark.createDataFrame()`** — builds small, controlled test data. Unit tests should never depend on production data.
- **`local[*]`** — runs Spark locally on your machine. No cluster needed.

---

## Setup

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

> `databricks-connect` bundles PySpark — uninstall standalone `pyspark` first if present.

---

## Running Tests

### From your terminal
```bash
pytest tests/ -v
```

### From a Databricks notebook
```python
import pytest, sys
sys.dont_write_bytecode = True
retcode = pytest.main(["tests/", "-v", "-p", "no:cacheprovider"])
assert retcode == 0
```

---

## Testing Approaches in Databricks

| Approach | Where it runs | Spark source | Speed | Best for |
|---|---|---|---|---|
| pytest locally | Your laptop | `local[*]` | Seconds | Pure logic + transforms |
| pytest in notebook | Databricks cluster | Cluster SparkSession | Medium | Integration tests |
| Databricks Connect | Your laptop | Remote cluster/Serverless | Medium | Testing against real infra |
| CI/CD pipeline | GitHub Actions etc. | `local[*]` or Connect | Varies | Automated on every PR |

---

## Requirements

| Package | Purpose |
|---|---|
| `databricks-connect>=18.0.0` | PySpark + optional remote execution |
| `databricks-sdk>=0.20.0` | Workspace API access |
| `python-dotenv>=1.0.0` | Local credential loading |
| `pytest>=8.0.0` | Test framework |
