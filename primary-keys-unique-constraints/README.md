# Primary Keys & Unique Constraints in Databricks

## The Problem

If you're coming from Oracle, SQL Server, or Postgres, you expect `PRIMARY KEY` and `UNIQUE` constraints to **reject bad writes**. On Databricks, they don't — they're **informational only**. No `ORA-00001`, no `duplicate key violates unique constraint`. Duplicates go right in.

This demo explains why, shows what to do about it today with PySpark/SQL, and demonstrates the long-term answer with DLT (now **LDP** — Lakeflow Declarative Pipelines) expectations.

## Who This Is For

DBAs and data engineers migrating from traditional RDBMS environments who want to understand how data integrity works on the lakehouse — and how to get the same guarantees they had before.

## Setup

```bash
cp .env.example .env
# Fill in your Databricks workspace details

python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Notebooks

Run in order: `00` → `01` → `02` → `03` → `04` → `05`.

| Notebook | Description | RDBMS Parallel |
|----------|-------------|----------------|
| `00_verify_connection` | Confirm Databricks Connect (serverless) and create the target schema | — |
| `01_generate_customer_data` | Generate ~200 customers, ~500 orders, and a batch with deliberate duplicates | Seed data |
| `02_pk_unique_constraints` | Add PK, UNIQUE, and FK constraints (idempotent); verify via `information_schema` | `ALTER TABLE ADD CONSTRAINT` |
| `03_constraints_not_enforced` | **The "aha" moment** — insert duplicates and orphans with zero errors | Where you'd expect `ORA-00001` |
| `04_enforce_with_pyspark_sql` | DIY enforcement: `NOT EXISTS`, validation functions, `MERGE`, FK checks | Stored procedures & triggers |
| `05_dlt_enforce_uniqueness` | **LDP (Lakeflow Declarative Pipelines) expectations** — clean run succeeds, dirty run fails on `expect_or_fail` | Engine-level PK/UNIQUE constraints |

## The Mental Model Shift

| RDBMS (Oracle, SQL Server, Postgres) | Lakehouse (Databricks) |
|---------------------------------------|------------------------|
| Engine enforces constraints at write time | Constraints are optimizer hints — enforcement is the pipeline's job |
| Stored procedures gate all writes | `MERGE` + validation in PySpark/SQL (day 1) |
| Triggers fire on bad data | LDP `expect_or_drop` / `expect_or_fail` (day 2) |
| `ORA-00001` rejects the INSERT | `expect_or_fail` halts the pipeline |
| One writer, one server, one lock manager | Distributed writers — no central lock to check against |

## LDP (Lakeflow Declarative Pipelines) Enforcement by Layer

| Layer | Enforcement | Why |
|-------|-------------|-----|
| **Bronze** | None | Raw landing zone — keep everything for debugging upstream issues |
| **Silver** | `expect_or_drop` | Filter nulls, bad formats, obvious junk (like CHECK constraints + triggers). Dropped rows are discarded, not quarantined. |
| **Gold** | `expect_or_fail` | Hard stop on duplicates or FK violations (like PK/UNIQUE constraints) |

## Key Takeaways

1. **PK/UNIQUE/FK constraints are informational** — they help the optimizer and BI tools but don't block bad writes
2. **Day 1: `MERGE` + post-write validation** in your existing PySpark/SQL jobs gets you enforcement now
3. **Day 2: LDP (Lakeflow Declarative Pipelines) expectations** give you centralized, declarative enforcement that can't be bypassed — the lakehouse equivalent of engine-level constraints
4. **Always declare constraints** in your DDL for optimizer hints and BI tool compatibility, even though they're not enforced
