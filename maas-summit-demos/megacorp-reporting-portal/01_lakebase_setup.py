# Databricks notebook source
# MAGIC %md
# MAGIC # 01 — Lakebase Setup: Multi-Tenant Reporting Portal
# MAGIC
# MAGIC This notebook provisions the full Lakebase infrastructure for the multi-tenant self-serve reporting portal.
# MAGIC
# MAGIC ## Architecture
# MAGIC ```
# MAGIC media_advertising (lakehouse)     →  Synced Tables  →  Lakebase (Postgres)
# MAGIC   gold.reach_cube                                       reach_cube (fast reads)
# MAGIC   gold.megacorp_user_frequency                          user_frequency
# MAGIC   gold.campaign_frequency_caps                          frequency_caps
# MAGIC
# MAGIC Lakebase also stores:
# MAGIC   tenants, users, sessions, saved_reports, feature_flags (app state)
# MAGIC   report_embeddings (pgvector — semantic search over saved reports)
# MAGIC ```
# MAGIC
# MAGIC ## Lakebase Features Demonstrated
# MAGIC | Feature | Use Case |
# MAGIC |---------|----------|
# MAGIC | **Scale-to-zero** | 5,000 advertiser tenants, 80% idle — pay only for active |
# MAGIC | **Branching** | Instant copy-on-write sandbox per tenant |
# MAGIC | **Synced Tables** | Sub-minute lakehouse → PG for fast portal loads |
# MAGIC | **pgvector** | Semantic search over saved reports |
# MAGIC | **UC + RLS** | Cross-tenant isolation at the data layer |

# COMMAND ----------

# MAGIC %pip install -U "databricks-sdk>=0.81.0" "psycopg[binary]>=3.0"
# MAGIC dbutils.library.restartPython()

# COMMAND ----------

# Configuration
PROJECT_ID = "adtech-portal"
DISPLAY_NAME = "AdTech Multi-Tenant Reporting Portal"
CATALOG = "alexander_booth"
SCHEMA = "adtech_portal"
PG_VERSION = "17"

# Source tables from media_advertising
SOURCE_CATALOG = "media_advertising"
TABLES_TO_SYNC = {
    f"{SOURCE_CATALOG}.gold.reach_cube": "reach_cube",
    f"{SOURCE_CATALOG}.gold.megacorp_user_frequency": "user_frequency",
    f"{SOURCE_CATALOG}.gold.campaign_frequency_caps": "frequency_caps",
    f"{SOURCE_CATALOG}.gold.forecasted_roas_gold": "forecasted_roas",
}

# COMMAND ----------

# MAGIC %md
# MAGIC ## Step 1: Create the Lakebase Project
# MAGIC
# MAGIC This creates a Lakebase Autoscaling project with:
# MAGIC - Production branch (default)
# MAGIC - Scale-to-zero enabled (suspends after 5 min idle)
# MAGIC - 0.5–4 CU autoscaling range

# COMMAND ----------

from databricks.sdk import WorkspaceClient
from databricks.sdk.service.postgres import (
    Project, ProjectSpec, Endpoint, EndpointSpec, FieldMask
)

w = WorkspaceClient()

# Create the project (idempotent — will error if exists)
try:
    operation = w.postgres.create_project(
        project=Project(
            spec=ProjectSpec(
                display_name=DISPLAY_NAME,
                pg_version=PG_VERSION
            )
        ),
        project_id=PROJECT_ID
    )
    result = operation.wait()
    print(f"✅ Created project: {result.name}")
except Exception as e:
    if "already exists" in str(e).lower():
        print(f"ℹ️  Project '{PROJECT_ID}' already exists — continuing")
    else:
        raise e

# COMMAND ----------

# Configure autoscaling and scale-to-zero on the primary endpoint
try:
    ep_name = f"projects/{PROJECT_ID}/branches/production/endpoints/ep-primary"
    w.postgres.update_endpoint(
        name=ep_name,
        endpoint=Endpoint(
            name=ep_name,
            spec=EndpointSpec(
                autoscaling_limit_min_cu=0.5,
                autoscaling_limit_max_cu=4.0,
                suspend_timeout_seconds=300  # Scale to zero after 5 min
            )
        ),
        update_mask=FieldMask(field_mask=[
            "spec.autoscaling_limit_min_cu",
            "spec.autoscaling_limit_max_cu",
            "spec.suspend_timeout_seconds"
        ])
    ).wait()
    print("✅ Configured autoscaling: 0.5–4 CU, scale-to-zero at 5 min")
except Exception as e:
    print(f"⚠️  Endpoint config: {e}")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Step 2: Connect and Create Application Tables
# MAGIC
# MAGIC These tables store portal state: tenant config, user sessions, saved reports, and feature flags.

# COMMAND ----------

import psycopg

# Get connection details
ep_name = f"projects/{PROJECT_ID}/branches/production/endpoints/ep-primary"
endpoint = w.postgres.get_endpoint(name=ep_name)
host = endpoint.status.hosts.host
cred = w.postgres.generate_database_credential(endpoint=ep_name)
username = w.current_user.me().user_name

conn_string = (
    f"host={host} "
    f"dbname=databricks_postgres "
    f"user={username} "
    f"password={cred.token} "
    f"sslmode=require"
)

print(f"🔗 Connecting to Lakebase: {host}")

# COMMAND ----------

# Create application schema and tables
DDL = """
-- Enable pgvector extension for semantic search
CREATE EXTENSION IF NOT EXISTS vector;

-- Portal application schema
CREATE SCHEMA IF NOT EXISTS portal;

-- Tenant registry (each distributor = one tenant)
CREATE TABLE IF NOT EXISTS portal.tenants (
    tenant_id TEXT PRIMARY KEY,
    display_name TEXT NOT NULL,
    distributor_name TEXT NOT NULL UNIQUE,  -- maps to media_advertising.*.distributor_name
    tier TEXT DEFAULT 'standard',           -- standard | premium | enterprise
    created_at TIMESTAMPTZ DEFAULT NOW(),
    settings JSONB DEFAULT '{}'
);

-- Portal users (advertiser logins)
CREATE TABLE IF NOT EXISTS portal.users (
    user_id TEXT PRIMARY KEY,
    tenant_id TEXT REFERENCES portal.tenants(tenant_id),
    email TEXT NOT NULL UNIQUE,
    display_name TEXT,
    role TEXT DEFAULT 'viewer',  -- viewer | analyst | admin
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Sessions for auth
CREATE TABLE IF NOT EXISTS portal.sessions (
    session_id TEXT PRIMARY KEY,
    user_id TEXT REFERENCES portal.users(user_id),
    tenant_id TEXT REFERENCES portal.tenants(tenant_id),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    expires_at TIMESTAMPTZ DEFAULT NOW() + INTERVAL '24 hours'
);

-- Saved reports with embeddings for semantic search
CREATE TABLE IF NOT EXISTS portal.saved_reports (
    report_id TEXT PRIMARY KEY,
    tenant_id TEXT REFERENCES portal.tenants(tenant_id),
    user_id TEXT REFERENCES portal.users(user_id),
    title TEXT NOT NULL,
    description TEXT,
    query_text TEXT,             -- the NL question or SQL
    result_snapshot JSONB,       -- cached results
    embedding vector(1536),      -- for semantic search
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Feature flags per tenant
CREATE TABLE IF NOT EXISTS portal.feature_flags (
    tenant_id TEXT REFERENCES portal.tenants(tenant_id),
    flag_name TEXT NOT NULL,
    enabled BOOLEAN DEFAULT FALSE,
    PRIMARY KEY (tenant_id, flag_name)
);

-- Watchlists (campaigns a tenant is tracking)
CREATE TABLE IF NOT EXISTS portal.watchlists (
    watchlist_id TEXT PRIMARY KEY,
    tenant_id TEXT REFERENCES portal.tenants(tenant_id),
    campaign_name TEXT NOT NULL,
    alert_threshold_freq INT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Indexes for fast lookups
CREATE INDEX IF NOT EXISTS idx_users_tenant ON portal.users(tenant_id);
CREATE INDEX IF NOT EXISTS idx_sessions_user ON portal.sessions(user_id);
CREATE INDEX IF NOT EXISTS idx_reports_tenant ON portal.saved_reports(tenant_id);
CREATE INDEX IF NOT EXISTS idx_watchlists_tenant ON portal.watchlists(tenant_id);
"""

with psycopg.connect(conn_string) as conn:
    conn.execute(DDL)
    conn.commit()
    print("✅ Created portal schema and all application tables")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Step 3: Seed Tenant Data
# MAGIC
# MAGIC Map the 5 MegaCorp distributors as tenants, each with demo users.

# COMMAND ----------

import uuid

TENANTS = [
    ("big-mountain", "Big Mountain Media", "Big Mountain", "enterprise"),
    ("curious-globe", "Curious Globe Networks", "Curious Globe", "premium"),
    ("rainbow-hemisphere", "Rainbow Hemisphere Inc", "Rainbow Hemisphere", "premium"),
    ("wily-one", "Wily One Digital", "Wily One", "standard"),
    ("large-mouse", "Large Mouse Entertainment", "Large Mouse", "enterprise"),
]

SEED_SQL = """
INSERT INTO portal.tenants (tenant_id, display_name, distributor_name, tier)
VALUES (%s, %s, %s, %s)
ON CONFLICT (tenant_id) DO UPDATE SET display_name = EXCLUDED.display_name;
"""

USER_SQL = """
INSERT INTO portal.users (user_id, tenant_id, email, display_name, role)
VALUES (%s, %s, %s, %s, %s)
ON CONFLICT (user_id) DO NOTHING;
"""

FLAG_SQL = """
INSERT INTO portal.feature_flags (tenant_id, flag_name, enabled)
VALUES (%s, %s, %s)
ON CONFLICT (tenant_id, flag_name) DO UPDATE SET enabled = EXCLUDED.enabled;
"""

with psycopg.connect(conn_string) as conn:
    for tid, name, dist, tier in TENANTS:
        conn.execute(SEED_SQL, (tid, name, dist, tier))
        # Create demo users per tenant
        conn.execute(USER_SQL, (
            f"{tid}-admin", tid, f"admin@{tid}.demo", f"{name} Admin", "admin"
        ))
        conn.execute(USER_SQL, (
            f"{tid}-analyst", tid, f"analyst@{tid}.demo", f"{name} Analyst", "analyst"
        ))
        # Feature flags
        conn.execute(FLAG_SQL, (tid, "sandbox_mode", tier in ("premium", "enterprise")))
        conn.execute(FLAG_SQL, (tid, "genie_chat", True))
        conn.execute(FLAG_SQL, (tid, "export_csv", tier == "enterprise"))
    conn.commit()
    print(f"✅ Seeded {len(TENANTS)} tenants with users and feature flags")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Step 4: Create Synced Tables (Reverse ETL)
# MAGIC
# MAGIC Sync gold-layer tables from the lakehouse into Lakebase for sub-5s portal reads.
# MAGIC This uses Databricks managed Lakeflow pipelines under the hood.

# COMMAND ----------

# First, ensure our target schema exists in the alexander_booth catalog
spark.sql(f"CREATE SCHEMA IF NOT EXISTS {CATALOG}.{SCHEMA}")
print(f"✅ Schema {CATALOG}.{SCHEMA} ready")

# COMMAND ----------

from databricks.sdk.service.database import (
    SyncedDatabaseTable, SyncedTableSpec, NewPipelineSpec,
    SyncedTableSchedulingPolicy
)

# NOTE: Synced tables require CDF on source. For this demo we use SNAPSHOT mode
# which does a full copy (no CDF needed).

for source_table, target_name in TABLES_TO_SYNC.items():
    full_target = f"{CATALOG}.{SCHEMA}.{target_name}"
    try:
        synced = w.database.create_synced_database_table(
            SyncedDatabaseTable(
                name=full_target,
                spec=SyncedTableSpec(
                    source_table_full_name=source_table,
                    scheduling_policy=SyncedTableSchedulingPolicy.SNAPSHOT,
                    new_pipeline_spec=NewPipelineSpec(
                        storage_catalog=CATALOG,
                        storage_schema=SCHEMA
                    )
                ),
            )
        )
        print(f"✅ Synced: {source_table} → {full_target}")
    except Exception as e:
        if "already exists" in str(e).lower():
            print(f"ℹ️  {full_target} already synced — skipping")
        else:
            print(f"⚠️  {full_target}: {e}")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Step 5: Create a Dev Branch (Sandbox Demo)
# MAGIC
# MAGIC This demonstrates branching — creating an instant copy-on-write sandbox.
# MAGIC In production, each advertiser who clicks "Enter Sandbox" gets their own branch.

# COMMAND ----------

from databricks.sdk.service.postgres import Branch, BranchSpec, Duration

try:
    branch = w.postgres.create_branch(
        parent=f"projects/{PROJECT_ID}",
        branch=Branch(
            spec=BranchSpec(
                source_branch=f"projects/{PROJECT_ID}/branches/production",
                ttl=Duration(seconds=86400)  # 24-hour expiry
            )
        ),
        branch_id="sandbox-demo"
    ).wait()
    print(f"✅ Created sandbox branch: {branch.name}")
    print("   This is an instant copy-on-write clone — zero data duplication!")
except Exception as e:
    if "already exists" in str(e).lower():
        print("ℹ️  sandbox-demo branch already exists")
    else:
        print(f"⚠️  Branch creation: {e}")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Step 6: Row-Level Security via UC
# MAGIC
# MAGIC Apply row filters on the synced tables so each tenant only sees their own data.
# MAGIC This is the **UC governance** layer — even if someone bypasses the app, the data layer enforces isolation.

# COMMAND ----------

# Create a function that checks the current user's tenant
spark.sql(f"""
CREATE OR REPLACE FUNCTION {CATALOG}.{SCHEMA}.tenant_filter(publisher STRING)
RETURNS BOOLEAN
COMMENT 'Row-level security filter: returns TRUE if the row belongs to the current tenant'
RETURN
  -- In production, this would look up the user's tenant from a mapping table
  -- For the demo, we pass tenant context via session variable
  publisher = current_user_attribute('tenant_publisher')
  OR is_account_group_member('adtech_portal_admins')
""")
print("✅ Created tenant_filter UDF for row-level security")
print("   In production: ALTER TABLE ... SET ROW FILTER tenant_filter ON (publisher)")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Step 7: Verify Setup
# MAGIC
# MAGIC Quick sanity check that everything is wired up correctly.

# COMMAND ----------

with psycopg.connect(conn_string) as conn:
    # Check tenants
    result = conn.execute("SELECT tenant_id, display_name, tier FROM portal.tenants ORDER BY tenant_id")
    print("\n📋 Registered Tenants:")
    print(f"{'Tenant ID':<22} {'Display Name':<30} {'Tier'}")
    print("-" * 65)
    for row in result:
        print(f"{row[0]:<22} {row[1]:<30} {row[2]}")
    
    # Check users
    result = conn.execute("SELECT COUNT(*) FROM portal.users")
    print(f"\n👥 Total users: {result.fetchone()[0]}")
    
    # Check feature flags
    result = conn.execute("SELECT COUNT(*) FROM portal.feature_flags WHERE enabled = true")
    print(f"🚩 Active feature flags: {result.fetchone()[0]}")
    
    # Check pgvector
    result = conn.execute("SELECT extversion FROM pg_extension WHERE extname = 'vector'")
    row = result.fetchone()
    print(f"🧠 pgvector version: {row[0] if row else 'NOT INSTALLED'}")

print("\n✅ Lakebase setup complete! Ready to deploy the portal app.")