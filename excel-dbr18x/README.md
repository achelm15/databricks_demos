# Excel Reading on DBR 18.x — Field Demo

Salt River Fields spring training data (attendance, concessions, merch) loaded from a multi-sheet Excel file using Databricks' **native Excel reader** — the correct replacement for the Crealytics connector removed in DBR 18.x.

---

## Background

The old `.format("excel")` pattern relied on the bundled Crealytics JAR (`com.crealytics.spark.excel`). **DBR 18.x / Serverless 18.0 removed this connector.** Customers on Serverless are automatically affected since it always tracks the latest runtime.

Databricks replaced it with a **native, first-party Excel data source** in DBR 17.1+. No JARs, no Maven packages, no pandas workarounds.

> **Note:** On current Serverless (Spark 4.1+), `format("excel")` no longer raises `AnalysisException` — it silently maps to the native reader. However, old Crealytics options like `header=True` and `inferSchema=False` are unrecognized by the native reader, causing it to return empty results. The migration is still required.

---

## The Migration

```python
# ❌ Before — Crealytics options silently ignored by native reader
spark.read \
    .format("excel") \
    .option("dataAddress", "'Sheet1'!A1:Z1000") \
    .option("header", True) \
    .option("inferSchema", False) \
    .load(file_path)

# ✅ After — native API, DBR 17.1+
spark.read \
    .option("dataAddress", "Sheet1") \
    .option("headerRows", 1) \
    .excel(file_path)
```

Or via SQL:
```sql
SELECT * FROM read_files("/Volumes/.../file.xlsx", format => 'excel', dataAddress => 'Sheet1', headerRows => 1)
```

---

## Native Reader — Key Rules

### Use `.option()` chaining, not kwargs
Keyword arguments passed directly to `.excel()` are silently ignored:
```python
# ❌ Options ignored — returns 0 rows, 0 cols
spark.read.excel(file_path, dataAddress="Sheet1", headerRows=1)

# ✅ Correct
spark.read.option("dataAddress", "Sheet1").option("headerRows", 1).excel(file_path)
```

### Use the sheet name as `dataAddress`, not a cell range
An explicit range like `A1:Z1000` forces the reader to return exactly that many rows/columns, padding empty cells with NULLs:
```python
# ❌ Returns 999 NULL-padded rows and 26 columns
.option("dataAddress", "Attendance!A1:Z1000")

# ✅ Auto-detects the used range
.option("dataAddress", "Attendance")
```

### No apostrophes around sheet names
```python
# ❌ Apostrophes cause empty results
.option("dataAddress", "'Attendance'")

# ✅ Bare sheet name
.option("dataAddress", "Attendance")
```

### Option name differences

| Crealytics (old) | Native (new) |
|---|---|
| `.option("header", True/False)` | `.option("headerRows", 0)` or `1` |
| `.option("inferSchema", ...)` | automatic — omit it |
| `.option("treatEmptyValuesAsNulls", ...)` | default behavior |
| `.option("dataAddress", "'Sheet'!A1:Z1000")` | `.option("dataAddress", "Sheet")` |
| n/a | `.option("operation", "listSheets")` |

---

## Discover Sheets at Runtime

```python
sheets_df = spark.read.option("operation", "listSheets").excel(file_path)
# Schema: sheetIndex (int), sheetName (string)
sheet_names = [row.sheetName for row in sheets_df.collect()]
```

---

## Notebooks

| Notebook | What it does |
|---|---|
| [00_verify_connection.ipynb](00_verify_connection.ipynb) | Connect to Serverless, create `salt_river_excel` schema + volume, upload sample Excel |
| [01_excel_reader.ipynb](01_excel_reader.ipynb) | Side-by-side: old broken pattern vs. native reader; SQL via `read_files()` |
| [02_multi_sheet.ipynb](02_multi_sheet.ipynb) | `listSheets` to enumerate sheets; multi-sheet loop; cross-sheet join |
| [03_write_to_delta.ipynb](03_write_to_delta.ipynb) | Type-cast and persist each sheet as a Delta table in UC |

Run them in order, starting with `00`.

---

## Sample Data

`sample_data/salt_river_fields.xlsx` — 2025 Cactus League season at Salt River Fields at Talking Stick (Rockies + D-backs spring training, Scottsdale AZ).

| Sheet | Rows | Columns |
|---|---|---|
| `Attendance` | 18 | game_date, home_team, opponent, attendance, capacity, pct_full, gate_revenue_usd |
| `Concessions` | 270 | game_date, home_team, item_name, category, unit_price_usd, units_sold, total_revenue_usd |
| `Merchandise` | 342 | game_date, home_team, sku, item_name, category, team, unit_price_usd, units_sold, total_revenue_usd |
| `Season_Summary` | 10 | metric, value |

Regenerate: `python3 sample_data/generate_sample.py`

---

## Setup

### 1. Install dependencies

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

> `databricks-connect` conflicts with a standalone `pyspark` install — uninstall `pyspark` first if present.

### 2. Configure credentials

```bash
cp .env.example .env
# Fill in DATABRICKS_HOST and DATABRICKS_TOKEN
```

### 3. Run notebooks in order

Start with `00_verify_connection.ipynb` — it creates the schema, volume, and uploads the Excel file to the UC Volume.

**No cluster needed.** Uses Serverless compute via `DatabricksSession.builder.serverless()`.

---

## UC Target

| | Value |
|---|---|
| Catalog | `alexander_booth` |
| Schema | `salt_river_excel` |
| Volume | `raw_files` |
| Delta tables | `attendance`, `concessions`, `merchandise` |

---

## Requirements

| Package | Purpose |
|---|---|
| `databricks-connect>=18.0.0` | Local → Serverless Spark execution |
| `databricks-sdk>=0.20.0` | File upload to UC Volume |
| `python-dotenv>=1.0.0` | Local credential loading |
| `openpyxl>=3.1.0` | Sample data generation only — not needed at runtime |
