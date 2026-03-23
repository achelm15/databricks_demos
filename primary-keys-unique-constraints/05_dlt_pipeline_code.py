"""
DLT Pipeline: Enforce Uniqueness with Expectations

Think of this as the lakehouse equivalent of your Oracle/SQL Server constraint stack:
  - Bronze: raw landing zone (no constraints — like a staging table)
  - Silver: CHECK constraints + BEFORE INSERT trigger equivalent (expect_or_drop)
  - Gold:   PRIMARY KEY / UNIQUE constraint equivalent (expect_or_fail)

The key difference: in the RDBMS world, constraints live in the storage engine.
Here, they live in the pipeline definition — declared once, enforced on every run.

Uploaded to the Databricks workspace by notebook 05_dlt_enforce_uniqueness.
"""

import dlt
from pyspark.sql.functions import col, count, lit


# -- Bronze: raw ingestion, no quality checks ----------------------------------
# RDBMS equivalent: a staging table with no constraints.
# We keep everything here — even bad data — so we can debug upstream issues.
# In Oracle, you'd lose visibility if a constraint rejected the row before you saw it.

@dlt.table(
    name="customers_bronze",
    comment="Raw customer batch — no quality checks applied (staging table equivalent)",
)
def customers_bronze():
    # Pipeline config is passed via spark.conf, not dlt.config
    catalog = spark.conf.get("uc_catalog")
    schema = spark.conf.get("uc_schema")
    return spark.read.table(f"{catalog}.{schema}.new_customers_batch")


# -- Silver: basic quality checks (drop bad rows) ------------------------------
# RDBMS equivalent: CHECK constraints + BEFORE INSERT triggers.
# expect_or_drop silently removes rows that fail — like a trigger that filters
# before the row hits the main table. The pipeline continues; bad rows are just gone.

@dlt.table(
    name="customers_silver",
    comment="Customers with null checks and email format validation (CHECK constraint equivalent)",
)
@dlt.expect_or_drop("customer_id_not_null", "customer_id IS NOT NULL")
@dlt.expect_or_drop("email_not_null", "email IS NOT NULL")
@dlt.expect_or_drop("valid_email_format", "email LIKE '%@%.%'")
@dlt.expect_or_drop("first_name_not_null", "first_name IS NOT NULL")
@dlt.expect_or_drop("last_name_not_null", "last_name IS NOT NULL")
def customers_silver():
    return dlt.read("customers_bronze")


# -- Gold: uniqueness enforcement (fail if duplicates exist) --------------------
# RDBMS equivalent: PRIMARY KEY and UNIQUE constraints.
# expect_or_fail halts the entire pipeline if ANY row violates the condition.
# This is the same behavior as ORA-00001 — the write is rejected, no bad data lands.
# The difference: you get clear metrics on WHAT failed, not just a cryptic error code.

@dlt.table(
    name="customers_gold",
    comment="Customers with uniqueness enforced — pipeline fails on duplicates (PK/UNIQUE equivalent)",
)
@dlt.expect_or_fail(
    "unique_customer_id",
    "id_count = 1",
)
@dlt.expect_or_fail(
    "unique_email",
    "email_count = 1",
)
def customers_gold():
    silver = dlt.read("customers_silver")

    # Add columns that count occurrences of each customer_id and email.
    # If any value appears more than once, the expectation fires and the pipeline halts.
    id_counts = silver.groupBy("customer_id").agg(count("*").alias("id_count"))
    email_counts = silver.groupBy("email").agg(count("*").alias("email_count"))

    return (
        silver
        .join(id_counts, on="customer_id", how="left")
        .join(email_counts, on="email", how="left")
    )
