# Team 8 — Building Brief: Multi-Tenant Self Serve Reporting on Lakebase

> **2026 MAAS SA Summit Workshop — Day 1 deliverable**
> Team 8: Joe Hu, Megan Tupper, Alexander Booth, Michelle Lui
> Use case: Multi-Tenant Self Serve Reporting

## 1. Use case framing

**Persona:** An ad agency ("AcmeAgency") runs paid media across many advertiser clients ("Patagonia," "Allbirds," "Bombas," etc.). Each advertiser logs into a branded self-serve portal to see *their own* spend, performance, audiences, and pacing — without ever seeing another advertiser's data.

**Why this is a Lakebase story, not an OLTP story:** The reporting numbers come from the lakehouse (campaign delivery logs, attribution joins, audience overlap models). But the tenant-facing app needs sub-100ms reads, per-tenant isolation, cheap idle cost, and the ability to spin up sandboxes for new advertisers in seconds. That's the seam Lakebase fits — *not* "we replaced your Postgres."

## 2. The Lakebase edge features we lead with

| Feature | How it shows up in the demo | The "why Lakebase" punchline |
|---|---|---|
| **Reverse sync (Lakehouse -> Lakebase)** | Gold reporting tables (`campaign_daily_perf`, `audience_segments`, `pacing_metrics`) synced into a Lakebase Postgres instance the app queries directly. | Lakehouse is the source of truth; tenants get OLTP-grade latency without an ETL pipeline you maintain. |
| **Scale-to-zero** | Smaller advertisers' DB instances idle to zero between logins; larger advertisers stay warm. | The multi-tenant economics: cost tracks active usage, not tenant count. |
| **Branching** | New advertiser onboarding ("Allbirds") spawns a branch from a template; sandbox/preview branch lets the agency model a campaign change before pushing live. | Tenant provisioning + safe what-if analysis without copy pipelines. |

> **Day-2 risk to manage:** Trying to land all three with the same depth produces a thin demo. Plan: **sync is the spine, scale-to-zero is told via the cost panel, branching is the "wow" moment shown via onboarding flow.** If we run out of time, branching is the first thing we cut, not sync.

## 3. Target solution architecture

```
+-------------------------------------------------------------+
| React frontend (Databricks App)                             |
|  - Tenant login / advertiser switcher                       |
|  - Self-serve dashboards: spend, performance, audiences     |
|  - "Sandbox this advertiser" -> spawns Lakebase branch      |
+--------------------------+----------------------------------+
                           | REST
+--------------------------v----------------------------------+
| FastAPI backend (Databricks App)                            |
|  - Auth + tenant routing (X-Forwarded-* headers)            |
|  - SQL to Lakebase per tenant                               |
|  - Branch lifecycle endpoints                               |
+--------------------------+----------------------------------+
                           | asyncpg
+--------------------------v----------------------------------+
| Lakebase Postgres (single instance, RLS by advertiser_id)   |
|  - Synced gold tables (read-only from lakehouse)            |
|  - Tenant config / app state (writable)                     |
+--------------------------^----------------------------------+
                           | reverse sync (Lakebase synced table)
+--------------------------+----------------------------------+
| Unity Catalog gold tables                                   |
|  campaign_daily_perf - audience_segments - pacing_metrics   |
+-------------------------------------------------------------+
```

**Architectural decision (resolved):** Single Lakebase instance with RLS by `advertiser_id`. Per-tenant instance is cleaner for branching/scale-to-zero economics but explodes provisioning complexity and Day-1 demo time. We keep one prod instance + branches for sandboxing/onboarding.

## 4. Data model (gold -> Lakebase)

Minimal but realistic:

- `advertisers` — tenant registry: id, name, tier, branch_id, brand_color
- `campaign_daily_perf` — advertiser_id, campaign_id, date, impressions, clicks, spend, conversions
- `audience_segments` — advertiser_id, segment_id, name, size, overlap_score
- `pacing_metrics` — advertiser_id, campaign_id, flight_to_date_spend, budget, days_remaining

Synthetic data: 9 advertisers, ~50 campaigns total, 84 days (12 weeks) of daily data. Deterministic via fixed seed. Generated in `00_setup.ipynb` via polars and stdlib (no PyPI deps required).

## 5. Day 1 / Day 2 plan

| Time | Day 1 (external agents) | Day 2 (Databricks-native) |
|---|---|---|
| 9:00-10:00 | Kickoff, repo scaffold, decide RLS vs per-tenant | Same repo, fresh branch — agent picks up where Day 1 left off |
| 10:00-12:00 | Generate gold data in UC; configure reverse sync to Lakebase | Rebuild data layer using Genie Code / Databricks Assistant |
| 12:00-13:00 | Lunch | Lunch |
| 13:00-15:00 | FastAPI + React app: login, advertiser switcher, 3 dashboards | Rebuild same with in-workspace AI / native agents |
| 15:00-16:30 | Branching: "Sandbox Allbirds" button -> new branch | Same, via native tooling |
| 16:30-17:00 | Cost panel showing scale-to-zero idle savings | Same |
| Day 2 last 30 min | — | **Readout:** demo + top 3 friction points + tagged feedback |

## 6. Feedback capture (per workshop spec)

Maintained live during Day 2 in a shared sheet, fields per the workshop doc:

`Task | Expected | Observed | Workaround | Severity | Native tool | Time lost (min)`

Each Team-8 member owns one slice of the build during Day 2 (data layer, FastAPI, React, branching). Each logs their own friction as they hit it — no one person batches at the end.

## 7. Day-2 final demo punchlist

What we have to be able to show in the Day-2 final demo:

1. Two advertisers logged in side-by-side, seeing different numbers
2. Click "spend by campaign" -> chart loads in <500ms (the Lakebase punchline)
3. Click "Onboard Allbirds" -> branch spawns, tenant appears within seconds
4. Cost panel: "AcmeAgency saved $X this month from 6 idle tenant DBs"
5. Day-2 readout slide: top 3 friction points from native agent build

Anything not on this list is out of scope for the workshop.

## 8. Repo layout

```
team-8-maas-summit/
  BRIEF.md                # this file
  README.md               # quickstart + deploy
  app.yaml                # Databricks Apps manifest
  requirements.txt        # backend deps (resolved at deploy)
  databricks.yml          # Asset Bundle
  notebooks/
    00_setup.ipynb              # catalog/schema, gold tables
    01_provision_lakebase.ipynb # create instance, synced tables, RLS
    02_demo_branching.ipynb     # show branch lifecycle end-to-end
  backend/
    main.py                # FastAPI app + middleware
    db.py                  # asyncpg pool with OAuth-token refresh
    config.py
    routers/
      advertisers.py
      campaigns.py
      audiences.py
      pacing.py
      branches.py
      cost.py
  frontend/
    package.json
    vite.config.ts
    index.html
    src/
      main.tsx
      App.tsx
      api.ts
      components/
        Layout.tsx
        AdvertiserSwitcher.tsx
        Dashboard.tsx
        SpendByCampaign.tsx
        AudienceOverlap.tsx
        PacingPanel.tsx
        SandboxButton.tsx
        CostPanel.tsx
        OnboardModal.tsx
  scripts/
    deploy.sh
    local_dev.sh
```
