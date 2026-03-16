# Delta Sharing → DuckDB & Pandas

Query a shared Delta table using DuckDB and pandas locally — **no SQL warehouse, no JDBC driver, no Databricks compute on the consumer side**. Uses fake NFL Combine data as the shared dataset.

---

## Background

Delta Sharing is an open protocol for secure data sharing. When the shared table is small, the consumer doesn't need a Databricks workspace or SQL warehouse at all. The `delta-sharing` Python library speaks the open protocol directly, and DuckDB provides a full in-process SQL engine on top of the result.

**Ideal for:**
- Sharing reference/lookup tables with external partners
- Lightweight analytics in notebooks without spinning up compute
- Data science workflows where pandas is the end goal anyway

---

## Architecture

```
┌──────────────────────────────────┐       ┌───────────────────────────────┐
│  PROVIDER (Databricks)           │       │  CONSUMER (Local Machine)     │
│                                  │       │                               │
│  alexander_booth                 │       │  delta-sharing python lib     │
│    .nfl_combine                  │       │       ↓                       │
│      .combine_results (Delta)    │──────▶│  pandas DataFrame             │
│                                  │ share │       ↓                       │
│  Unity Catalog Share             │ profile│  DuckDB (in-process SQL)     │
│    └─ nfl_combine_share          │ .json │       ↓                       │
│        └─ combine_results        │       │  SELECT * FROM ...            │
│                                  │       │  No warehouse needed!         │
└──────────────────────────────────┘       └───────────────────────────────┘
```

---

## Notebooks

| Notebook | Description |
|----------|-------------|
| [00_verify_connection.ipynb](00_verify_connection.ipynb) | Connect to Serverless, create `nfl_combine` schema |
| [01_generate_combine_data.ipynb](01_generate_combine_data.ipynb) | Generate 300 fake NFL Combine records with `faker`, write to Delta |
| [02_setup_delta_sharing.ipynb](02_setup_delta_sharing.ipynb) | Create share + recipient, download `share_profile.json` |
| [03_consumer_duckdb_pandas.ipynb](03_consumer_duckdb_pandas.ipynb) | **The demo** — query shared data with DuckDB & pandas, zero warehouse cost |

Run them in order, starting with `00`.

- **Notebooks 00–02:** Provider-side setup (requires Databricks credentials)
- **Notebook 03:** Consumer-side demo (only needs `share_profile.json`)

---

## Sample Data

300 rows of fake NFL Combine results generated with `faker`.

| Column | Type | Example |
|--------|------|---------|
| `player_name` | string | James Lewis |
| `position` | string | WR, QB, RB, ... (14 positions) |
| `college` | string | Alabama, Ohio State, ... (34 schools) |
| `height_in` | int | 73 |
| `weight_lbs` | int | 215 |
| `forty_yard_dash` | double | 4.35 |
| `bench_press_reps` | int | 22 |
| `vertical_jump_in` | double | 35.5 |
| `broad_jump_in` | int | 121 |
| `three_cone_drill` | double | 7.01 |
| `shuttle_20yd` | double | 4.22 |
| `draft_year` | int | 2023, 2024, 2025 |

---

## Setup

### 1. Install dependencies

```bash
pip install -r requirements.txt
```

> **Note:** `databricks-connect` conflicts with standalone `pyspark` — uninstall `pyspark` first if present.

### 2. Configure credentials

```bash
cp .env.example .env
# Fill in DATABRICKS_HOST and DATABRICKS_TOKEN
```

### 3. Run notebooks 00–02 (provider setup)

Creates the table, share, recipient, and downloads `share_profile.json`.

### 4. Run notebook 03 (consumer demo)

Only needs `share_profile.json`. No Databricks credentials required.

**Compute:** Provider setup uses Serverless via `DatabricksSession.builder.serverless()`. Consumer side uses no Databricks compute at all.

---

## Limitations

This approach is designed for **small datasets**. Be aware of the following:

| Limitation | Details |
|------------|---------|
| **Memory** | `delta_sharing.load_as_pandas()` loads the **entire table into memory**. Tables must be small enough to fit in your local RAM (e.g., hundreds to low hundreds of thousands of rows, depending on schema). |
| **No predicate pushdown** | DuckDB queries run locally *after* the full table is fetched. There is no `WHERE` pushdown to the provider — you always pull the whole table first. |
| **Network transfer** | The full dataset is transferred over the network. Large tables mean slow fetches and high bandwidth use. |
| **Best fit** | Reference tables, lookup data, small fact tables. **Not** suitable for large analytical datasets or tables with millions of rows. |

For larger shared tables, consumers should use Databricks SQL warehouses, Spark, or other engines that support streaming/chunked reads.

---

## UC Target

| | Value |
|---|------|
| Catalog | `alexander_booth` |
| Schema | `nfl_combine` |
| Delta table | `combine_results` |
| Share | `nfl_combine_share` |
| Recipient | `nfl_combine_external_reader` |

---

## Requirements

| Package | Purpose |
|---------|---------|
| `databricks-connect>=18.0.0,<18.1.0` | Local → Serverless Spark execution (provider setup) |
| `databricks-sdk>=0.20.0` | Recipient management via REST API (provider setup) |
| `python-dotenv>=1.0.0` | Local credential loading |
| `faker>=25.0.0` | Data generation only |
| `delta-sharing>=1.0.0` | Open protocol client (consumer) |
| `duckdb>=1.0.0` | In-process SQL engine (consumer) |
| `pandas>=2.0.0` | DataFrame operations (consumer) |
| `pyarrow>=14.0.0` | Columnar data transport (consumer) |
