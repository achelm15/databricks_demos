# Hockey Schema Monitoring — UI walkthrough

This is the click-by-click for demoing the alerts + monitoring + schema-evolution story through the Databricks UI. The notebooks themselves only exist to seed state and trigger the change — everything the audience sees is in the workspace UI.

---

## 0. Get the notebooks into the workspace

You want the notebooks **in the workspace** so you can show them in the Notebook UI (not run locally via Connect). Two options for the field-eng (`field-eng.cloud.databricks.com`) workspace:

### Option A — Databricks CLI `workspace import-dir` (fastest, recommended)

```bash
# from the repo root
databricks workspace import-dir \
    hockey-schema-monitoring/ \
    /Workspace/Users/alexander.booth@databricks.com/hockey-schema-monitoring \
    --overwrite \
    --profile field-eng
```

If you don't have a `field-eng` CLI profile yet:

```bash
databricks configure --host https://e2-demo-field-eng.cloud.databricks.com --profile field-eng
# paste a PAT when prompted
```

This uploads all `.ipynb` files as workspace notebooks (Databricks auto-converts `.ipynb` ↔ Databricks notebook format).

### Option B — Drag-and-drop in the UI

Workspace → Users → your email → right-click → **Import** → drag the six `.ipynb` files in. Less ergonomic than the CLI but useful if you can't run a shell on the demo machine.

### Option C — Git Folder (if you want history visible)

Workspace → Create → **Git folder** → point at this repo (HTTPS or SSH). Audience sees a real branch + commit, which lands well with platform/IT folks.

After upload, your notebooks live at:

```
/Workspace/Users/alexander.booth@databricks.com/hockey-schema-monitoring/
    00_setup
    01_bronze_variant_v1
    02_silver_projection
    03_drift_detector_and_monitoring
    04_simulate_api_v2
    05_schema_evolution
```

> Once they're in the workspace, the notebooks use the in-workspace `spark` automatically — no `.env` needed, no local Python. The `try: spark / except NameError` pattern at the top of every notebook handles both modes.

---

## 1. Pre-demo seeding (run this *before* the audience joins)

Open the workspace notebooks and run, in order:

1. **`00_setup`** — Run All. Creates `<catalog>.hockey_schema_monitoring_bronze` / `_silver` / `_silver_monitoring` schemas. ~10s.
2. **`01_bronze_variant_v1`** — Run All. Lands ~3,200 v1 events into `bronze.plays_raw` (VARIANT payload). ~30s.
3. **`02_silver_projection`** — Run All. Builds `silver.plays` from the known v1 keys + writes the allow-list. ~30s.
4. **`03_drift_detector_and_monitoring`** — Run All. Builds the drift view, creates the Lakehouse Monitor on silver, kicks off the first refresh. ~1 min; the LHM refresh takes 1–3 more minutes in the background.

At this point everything is set up — drift view is empty (no drift yet), monitor is initialised, silver has v1 data only.

> **Tip:** if the demo machine has good wifi, you can run 04+05 live; if it doesn't, dry-run them once before the demo to warm the cluster cache, then re-run live.

---

## 2. The audience-facing flow

### Part 1 — "Here's the bronze table, payload is VARIANT"

**Where:** Catalog Explorer

1. Sidebar → **Catalog** → `<your_catalog>` → `hockey_schema_monitoring_bronze` → `plays_raw`
2. **Overview** tab — point at the `payload` column. Type is **`VARIANT`**.
3. **Sample Data** tab — show the JSON values inline. Make the point: *"This API can add or rename keys tomorrow and ingest doesn't break."*
4. Open a new **SQL Editor** tab and paste:
   ```sql
   SELECT payload:event_type::string, payload:team_abbrev::string, payload:x_coord::int, payload:y_coord::int
   FROM hockey_schema_monitoring_bronze.plays_raw
   LIMIT 10;
   ```
   Run it. Make the point: *"VARIANT lets us query it like JSON without parsing — but downstream consumers still want typed columns, hence silver."*

### Part 2 — "Silver is the typed projection, here's the contract"

**Where:** Catalog Explorer

1. Open `hockey_schema_monitoring_silver.plays` — point at the typed columns.
2. Open `hockey_schema_monitoring_silver.known_payload_keys` → **Sample Data** — *"This is the contract. If a key shows up in payload that isn't in this list, that's drift."*
3. Open `hockey_schema_monitoring_silver.v_unknown_payload_keys` (the view) → **Sample Data** — should be empty. *"Today we're clean."*

### Part 3 — "Create the DBSQL Alert"

**Where:** Sidebar → **Alerts** → **Create Alert**

New-style alerts embed the query directly — there is no separate saved-query step, and query parameters are not supported (so fully-qualify the view name).

1. Sidebar → **Alerts** → **Create Alert**
2. Paste the contents of `alerts/drift_alert.sql` into the alert's built-in query editor → click **Run** (should return 0 rows right now)
3. **Condition**:
   - Column: `sightings`
   - Aggregation: `Sum` (or `Count`)
   - Operator: `> 0`
4. **Schedule**: every **5 minutes** (or use **Refresh now** during the live demo)
5. **Notifications**: search for your username, or add a Slack / email destination
6. **Name**: `Hockey — unknown payload keys`
7. Click **View alert** to save. State shows **OK**.

> If you want to import the saved config from this repo verbatim, the JSON is in `Hockey — unknown payload keys.dbalert.json` (Sidebar → Alerts → ⋯ → **Import**).

### Part 4 — "Lakehouse Monitoring covers the other half"

**Where:** Catalog Explorer → silver table → Quality tab

1. Back to `hockey_schema_monitoring_silver.plays` → **Quality** tab.
2. Point at the monitor that notebook 03 created — *"This profiles every column. Notice it has no idea about keys we *don't* have columns for — that's why we need both signals."*
3. Click **View dashboard** (opens the auto-generated LHM dashboard) — distributions, null %, freshness chart, etc.
4. Show the underlying metrics tables: `hockey_schema_monitoring_silver_monitoring.plays_profile_metrics` and `_drift_metrics`. *"These are just Delta tables. You can build your own alert on them too."*

### Part 5 — "The API ships v2 with three new keys" *(this is the live trigger)*

**Where:** Workspace → notebook `04_simulate_api_v2`

1. Open the notebook, narrate the markdown cell: *"NHL EDGE-style API just added expected_goals, shot_quality_index, puck_speed_mph."*
2. **Run All**. ~15s.
3. Scroll to the last output — drift detector now shows 3 rows.
4. Switch back to the SQL Editor with the alert query open → **Refresh** — shows 3 rows.

### Part 6 — "The alert fires"

**Where:** Sidebar → **Alerts** → **Hockey — unknown payload keys**

1. Click **Refresh now** on the alert (or wait for the next scheduled run).
2. State flips to **Triggered**.
3. Check email — message arrives with the three keys in the body.
4. Click into the alert and show the **History** tab — point at the state transition timeline.

> **Talking point:** *"This is the gap LHM doesn't catch. LHM only knows about columns that exist. Schema drift in the payload happens before silver ever sees it."*

### Part 7 — "We absorb the new keys" *(schema evolution)*

**Where:** Workspace → notebook `05_schema_evolution`

1. Open the notebook, narrate the markdown: *"Triage says these are real keys we want. Two steps: widen the allow-list, widen silver."*
2. **Run All**. ~30s.
3. Switch back to Catalog Explorer → `silver.plays` → **Overview** → point at the three new columns (`expected_goals`, `shot_quality_index`, `puck_speed_mph`).
4. Switch back to the alert → **Refresh now** — flips back to **OK**.
5. Re-open the LHM dashboard (or trigger a refresh via the **Refresh** button in the Quality tab) — within 1–3 minutes the dashboard shows the three new columns profiled.

> **Talking point:** *"VARIANT in bronze meant the v2 data was never lost — we just hadn't surfaced it yet. Delta `mergeSchema` widened silver without rewriting history. Lakehouse Monitoring picked up the new columns automatically."*

### Part 8 — "Job-level alerts cover the operational case"

**Where:** Workspace → Jobs

1. Sidebar → **Workflows** → **Create Job**
2. Use **`jobs/strict_silver_job.json`** as a reference (or paste it into the JSON editor):
   - Two tasks: `drift_guard` (runs notebook 03) → `silver_projection` (runs notebook 02)
   - `email_notifications.on_failure` → your email
   - Schedule: hourly
3. Show the **Email notifications** section in the job UI — *"If the drift_guard task or the silver projection ever fails, this fires immediately. Webhook destinations work the same way for Slack / PagerDuty / Teams."*
4. **Run now** → show the run history.

---

## 3. Cleanup (after the demo)

```bash
# from the repo root
databricks sql --profile field-eng <<'EOF'
DROP SCHEMA IF EXISTS <catalog>.hockey_schema_monitoring_bronze CASCADE;
DROP SCHEMA IF EXISTS <catalog>.hockey_schema_monitoring_silver CASCADE;
DROP SCHEMA IF EXISTS <catalog>.hockey_schema_monitoring_silver_monitoring CASCADE;
EOF
```

Or, in the workspace: open `00_setup`, uncomment the **Optional reset** cell, run that one cell.

The Lakehouse Monitor is tied to the silver table, so dropping the schema removes it. The DBSQL Alert persists — delete it from the **Alerts** page (new-style alerts embed the query, so there's no separate saved-query to clean up).

---

## 4. Quick reference — the three alert mechanisms side by side

| Mechanism | What it watches | Where you configure it | Where it fires |
|---|---|---|---|
| **DBSQL Alert on drift view** | New top-level keys in `bronze.plays_raw.payload` (VARIANT) | Sidebar → Alerts → Create Alert (new-style; query embedded) | Email / Slack / PagerDuty / MS Teams |
| **Lakehouse Monitor** | Profile + drift stats on existing silver columns | Catalog Explorer → Quality tab (or `WorkspaceClient.lakehouse_monitors`) | LHM dashboard + drift metrics table (which you can alert on with another DBSQL alert) |
| **Job email_notifications** | Pipeline failures (e.g. strict-mode projection failing on unknown casts) | Workflows → Job config | Email / webhook |
