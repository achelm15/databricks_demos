# Databricks notebook source
# MAGIC %md
# MAGIC # 02 — Demo Walkthrough: Multi-Tenant Self-Serve Reporting Portal
# MAGIC
# MAGIC ## The Story
# MAGIC
# MAGIC You are **MegaCorp**, a media conglomerate running 7 ad campaigns across CTV, mobile, and web.  
# MAGIC You have **5 distributor partners** (Big Mountain, Curious Globe, Rainbow Hemisphere, Wily One, Large Mouse) who each need a **self-serve portal** to view their campaign performance.
# MAGIC
# MAGIC ### The Problem (Legacy Stack)
# MAGIC | Pain | Legacy Answer | Cost |
# MAGIC |------|---------------|------|
# MAGIC | 5,000 advertiser tenants, 80% idle | Always-on per-tenant DB | $$$$ |
# MAGIC | Every advertiser wants a sandbox | Months of infra work | Engineering time |
# MAGIC | Cross-tenant data leakage risk | Bolt-on app-layer auth | Compliance risk |
# MAGIC | Reports slow (hit lakehouse) | Separate cache + sync ETL | Maintenance |
# MAGIC | Customers want NL chat | Bolt on vector DB + LLM | Complexity |
# MAGIC
# MAGIC ### The Solution (Lakebase)
# MAGIC | Pain | Lakebase Answer |
# MAGIC |------|----------------|
# MAGIC | Idle tenants bleed money | **Scale-to-zero** — pay per active tenant |
# MAGIC | Sandbox takes months | **Branching** — instant copy-on-write clone |
# MAGIC | Cross-tenant leakage | **UC + Postgres RLS** — governed at data layer |
# MAGIC | Slow reports | **Synced tables** — lakehouse → PG, managed |
# MAGIC | NL chat over data | **pgvector + Genie** — single stack |

# COMMAND ----------

# MAGIC %md
# MAGIC ## Architecture Diagram
# MAGIC
# MAGIC ```
# MAGIC ┌─────────────────────────────────────────────────────────────────────┐
# MAGIC │                        DATABRICKS LAKEHOUSE                          │
# MAGIC │                                                                       │
# MAGIC │  media_advertising.gold.reach_cube         (campaign reach rollups)   │
# MAGIC │  media_advertising.gold.campaign_reach_metrics  (UC Metric View)      │
# MAGIC │  media_advertising.gold.megacorp_user_frequency (frequency data)      │
# MAGIC │                                                                       │
# MAGIC └────────────────────────────────┬──────────────────────────────────────┘
# MAGIC                                  │
# MAGIC                          Synced Tables (Reverse ETL)
# MAGIC                          Sub-minute latency
# MAGIC                                  │
# MAGIC                                  ▼
# MAGIC ┌─────────────────────────────────────────────────────────────────────┐
# MAGIC │                        LAKEBASE (Postgres)                           │
# MAGIC │                                                                       │
# MAGIC │  reach_cube (synced)          ← Fast reads for dashboard              │
# MAGIC │  user_frequency (synced)      ← Frequency analysis                   │
# MAGIC │  frequency_caps (synced)      ← Cap monitoring                       │
# MAGIC │                                                                       │
# MAGIC │  portal.tenants               ← Tenant registry                      │
# MAGIC │  portal.users                 ← Portal auth                          │
# MAGIC │  portal.saved_reports         ← With pgvector embeddings             │
# MAGIC │  portal.feature_flags         ← Per-tenant features                  │
# MAGIC │                                                                       │
# MAGIC │  Features: Scale-to-zero │ Branching │ pgvector │ UC RLS             │
# MAGIC └────────────────────────────────┬──────────────────────────────────────┘
# MAGIC                                  │
# MAGIC                                  ▼
# MAGIC ┌─────────────────────────────────────────────────────────────────────┐
# MAGIC │                     DATABRICKS APP (React + FastAPI)                  │
# MAGIC │                                                                       │
# MAGIC │  Login (tenant-select) → Dashboard (isolated metrics) → Genie Chat   │
# MAGIC │                        → Saved Reports (pgvector search)              │
# MAGIC │                        → Sandbox Mode (branching)                     │
# MAGIC │                                                                       │
# MAGIC │  + campaign_reach_qa Genie Space (NL → SQL against Metric View)      │
# MAGIC └───────────────────────────────────────────────────────────────────────┘
# MAGIC ```

# COMMAND ----------

# MAGIC %md
# MAGIC ## Demo Script (5 minutes)
# MAGIC
# MAGIC ### Act 1: Multi-Tenant Isolation (UC + RLS)
# MAGIC 1. Open the portal → Login as **Big Mountain Media** (enterprise tier)
# MAGIC 2. See campaign metrics → *Only* Big Mountain's data appears
# MAGIC 3. Switch tenant (logout → login as **Wily One Digital**) → Completely different data
# MAGIC 4. **Key point:** "UC row-level security enforces this at the data layer — even if the app has a bug, data can't leak."
# MAGIC
# MAGIC ### Act 2: Fast Reads via Synced Tables
# MAGIC 1. Show the dashboard loading in <2 seconds
# MAGIC 2. **Key point:** "This data lives in the lakehouse (Delta). Lakebase synced tables replicate it to Postgres in sub-minute intervals. The portal reads from Postgres — fast, without hitting Spark."
# MAGIC
# MAGIC ### Act 3: NL Queries via Genie
# MAGIC 1. Click "Ask Genie" tab
# MAGIC 2. Ask: "What is my total reach across all campaigns?"
# MAGIC 3. Genie queries the `campaign_reach_metrics` Metric View, scoped to the tenant
# MAGIC 4. **Key point:** "The Genie space uses the UC Metric View — governed definitions, not raw SQL. And the query is automatically filtered to this tenant's data."
# MAGIC
# MAGIC ### Act 4: Branching as Sandbox
# MAGIC 1. Click "Sandbox" → "Create Sandbox Branch"
# MAGIC 2. Branch created in ~2 seconds
# MAGIC 3. **Key point:** "That just created a full copy-on-write clone of the production database. Zero data duplication. The advertiser can now test audience segments, adjust frequency caps, run what-ifs — without any risk to production."
# MAGIC 4. Show branch expires in 1 hour (auto-cleanup)
# MAGIC
# MAGIC ### Act 5: Scale-to-Zero
# MAGIC 1. Show the Lakebase project config: 0.5–4 CU, scale-to-zero at 5 min
# MAGIC 2. **Key point:** "We have 5,000 advertiser tenants. 80% are idle at any time. With scale-to-zero, we only pay for compute when an advertiser is actively using the portal. That's the difference between $50K/month and $5K/month."
# MAGIC
# MAGIC ### Closing
# MAGIC "This is not a feature demo — it's an architecture demo. Log in as Advertiser A → see only your data (UC) → branch into a sandbox (branching) → ask the agent a question (Genie + pgvector) → see fresh metrics (synced tables) → portal scales for the next tenant (autoscaling). It maps directly to a budget line item the customer is already trying to fund."

# COMMAND ----------

# MAGIC %md
# MAGIC ## Project Structure
# MAGIC
# MAGIC ```
# MAGIC multi-tenant-reporting-portal/
# MAGIC ├── 01_lakebase_setup.ipynb        ← Run first: provisions Lakebase + seeds data
# MAGIC ├── 02_demo_walkthrough.ipynb       ← This file: demo script & architecture
# MAGIC └── app/
# MAGIC     ├── app.yaml                    ← Databricks App deployment config
# MAGIC     ├── backend/
# MAGIC     │   ├── main.py                 ← FastAPI: Lakebase queries, Genie, auth
# MAGIC     │   └── requirements.txt
# MAGIC     └── frontend/
# MAGIC         ├── package.json
# MAGIC         ├── vite.config.ts
# MAGIC         ├── tsconfig.json
# MAGIC         ├── index.html
# MAGIC         └── src/
# MAGIC             ├── main.tsx
# MAGIC             ├── App.tsx              ← Router + auth guard
# MAGIC             ├── api.ts              ← API client
# MAGIC             ├── pages/
# MAGIC             │   ├── Login.tsx       ← Tenant selection
# MAGIC             │   ├── Dashboard.tsx   ← Campaign metrics
# MAGIC             │   └── Sandbox.tsx     ← Branching demo
# MAGIC             └── components/
# MAGIC                 ├── MetricsGrid.tsx  ← Charts (Recharts)
# MAGIC                 ├── GenieChat.tsx    ← NL query interface
# MAGIC                 └── SavedReports.tsx ← pgvector search
# MAGIC ```

# COMMAND ----------

# MAGIC %md
# MAGIC ## Deployment Steps
# MAGIC
# MAGIC ### 1. Run the Setup Notebook
# MAGIC ```
# MAGIC Run 01_lakebase_setup.ipynb — creates Lakebase project, tables, seeds tenants
# MAGIC ```
# MAGIC
# MAGIC ### 2. Deploy the App
# MAGIC ```bash
# MAGIC # From the workspace, deploy via Databricks Apps
# MAGIC cd multi-tenant-reporting-portal/app
# MAGIC databricks apps create adtech-portal --manifest app.yaml
# MAGIC databricks apps deploy adtech-portal
# MAGIC ```
# MAGIC
# MAGIC ### 3. Configure Genie Space
# MAGIC Set the `GENIE_SPACE_ID` environment variable in app.yaml to point to the
# MAGIC `campaign_reach_qa` Genie space (already exists in the media_advertising domain).
# MAGIC
# MAGIC ### 4. Test
# MAGIC - Login as each tenant
# MAGIC - Verify data isolation
# MAGIC - Ask Genie questions
# MAGIC - Create a sandbox branch

# COMMAND ----------

# MAGIC %md
# MAGIC ## Conversation Hooks for Sales
# MAGIC
# MAGIC | Segment | Hook |
# MAGIC |---------|------|
# MAGIC | **RMN buyer** | "You're trying to be Amazon Ads for your retail. Building the portal is the hard part. We give you Apps + Lakebase as the platform so your team can focus on measurement and audience innovation, not auth and sync pipelines." |
# MAGIC | **CTV/streaming** | "Your ad business is growing faster than your data engineering team. Lakebase lets one team serve thousands of advertiser portals without an OLTP fleet to babysit." |
# MAGIC | **Agency** | "Each client wants a branded view of their cross-channel spend. Branching gives you per-client sandboxes; UC governs PII; the agent answers their questions." |
# MAGIC | **Publisher** | "You already have the lakehouse for yield analytics. Lakebase turns the same data into an advertiser-facing portal in days, not quarters." |

# COMMAND ----------

# Quick verification: show the data that powers the portal
display(spark.sql("""
  SELECT publisher, campaign, device_type,
         SUM(reach_ind) as reach, SUM(matched_imps) as impressions
  FROM media_advertising.gold.reach_cube
  WHERE publisher != 'All'
  GROUP BY publisher, campaign, device_type
  ORDER BY publisher, reach DESC
  LIMIT 20
"""))