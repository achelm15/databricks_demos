# rostr-artist-team-enrichment

Nightly enrichment of an artists Google Sheet with **agency** and **management**
contacts pulled from [rostr.cc](https://www.rostr.cc).

**Demo flow:**

1. Read a Google Sheet with one row per artist.
2. For every row missing any of `Agency / Agent Name / Management / Management Contact`,
   look the artist up on rostr.cc.
3. Write the missing values back to the sheet (only blank cells — manual edits are preserved).
4. Stamp `Last Updated` (UTC).

The sheet → rostr.cc → sheet path needs **no Spark, no Databricks Connect, no
headless browser**. It's a 2-notebook demo that runs anywhere Python runs. An
optional UC Volume + Delta history table is one env-var away if the customer
wants an audit trail.

---

## Files

| File | Purpose |
|---|---|
| `databricks_ui_single_notebook_demo.ipynb` | **Start here for a walkthrough.** Self-contained — runs in the Databricks UI with all code inline and credentials hardcoded at the top. No `.env`, no Databricks Connect, no module imports. |
| `00_verify_connection.ipynb` | Confirms rostr.cc login + Google Sheet read before you start the demo (local-dev flow with `.env`) |
| `01_enrich_artists.ipynb`    | The job split across notebook + module files (local-dev flow with `.env`) |
| `rostr_client.py`            | Thin client around rostr.cc's JSON API (`/v1/auth/rostr` + `/v1/artist/{handle}/team/{ROLE}`) |
| `sheets_client.py`           | Google Sheets v4 read/update with both `adc` (laptop) and `service` (job) auth modes |
| `create_job.py`              | One-shot helper to create the nightly Databricks Job from `databricks-sdk` |
| `requirements.txt`, `.env.example` | Standard demo scaffolding |

> **TL;DR for the walkthrough:** import `databricks_ui_single_notebook_demo.ipynb` into a Databricks workspace, paste in the rostr.cc creds + sheet ID + service-account JSON at the top, and run the cells top-to-bottom. Everything else in this folder is the original split-across-files version.

---

## Setup

```bash
cd rostr-artist-team-enrichment

# Use whatever Python env you like. The demo relies on requests + google-auth +
# python-dotenv. databricks-connect/databricks-sdk are only needed when
# PERSIST_TO_UC=true.
pip install -r requirements.txt

cp .env.example .env
# Fill in:
#   ROSTR_USERNAME, ROSTR_PASSWORD     - your rostr.cc account
#   GOOGLE_SHEET_ID, GOOGLE_SHEET_TAB  - the sheet to enrich
#   GOOGLE_AUTH_MODE                   - `adc` for local dev, `service` for the job
```

Then for **local dev** Google auth:

```bash
gcloud auth application-default login --quiet
gcloud auth application-default set-quota-project gcp-sandbox-field-eng
```

Run `00_verify_connection.ipynb` end-to-end, then `01_enrich_artists.ipynb`.

---

## How rostr.cc auth works

The rostr.cc *web UI* is gated by Cloudflare Turnstile + a Castle.io fraud
token, but the *underlying JSON API* only requires email + password — fraud
checks are enforced at the web origin only. So we just:

```python
session.post("https://api.rostr.cc/v1/auth/rostr",
             json={"email": user, "password": pw})    # 201, sets rack.session cookie
session.get("https://api.rostr.cc/v1/artist/{handle}/team/MANAGEMENT")
session.get("https://api.rostr.cc/v1/artist/{handle}/team/AGENCY")
```

The session cookie is cached in `ROSTR_COOKIE_PATH` so we don't re-login on
every run. If rostr.cc ever 401s, the client just re-logs-in transparently.

---

## Sheet schema

The demo expects the columns shown below. The original sheet had a typo
(`Mangement Contact`); `sheets_client.ensure_canonical_header()` fixes it
in-place on first run.

| Col | Header | Source |
|---|---|---|
| A | Artist | Manual |
| B | Agency | rostr `team/AGENCY → company.name` |
| C | Agent Name | rostr `team/AGENCY → team[].people[].name` (joined) |
| D | Management | rostr `team/MANAGEMENT → company.name` (joined) |
| E | Management Contact | First manager email/phone, falls back to first manager name |
| F | Last Updated | ISO-8601 UTC, minute precision, written when any cell on the row was filled |

Optional column `Rostr Handle` — if present, the value in this column is used as the rostr.cc URL slug instead of slugifying the artist name (helpful for unusual names, e.g. "P!nk").

---

## Optional: persist to Unity Catalog

Flip `PERSIST_TO_UC=true` in `.env` to also land:

* the raw rostr API responses for each artist in `/Volumes/{cat}/{schema}/raw_data/{run_ts}/{slug}.json`
* one row per `(run_ts, artist, role)` in `{cat}.{schema}.team_enrichment_history` — gives you a full Delta-tracked audit log of "what did rostr say on day X"

When this is on, you'll need `databricks-connect` + `databricks-sdk` from `requirements.txt` (they're optional otherwise).

---

## Scheduling as a nightly Databricks Job

Once you've validated the demo locally, create the nightly job with the helper:

```bash
# These come from your .env or workspace defaults
export DATABRICKS_HOST=https://your-workspace.cloud.databricks.com
export DATABRICKS_TOKEN=dapiXXXXXXXXXXXXXXXX
export NOTEBOOK_WORKSPACE_PATH=/Workspace/Users/you@databricks.com/rostr-artist-team-enrichment/01_enrich_artists

python create_job.py
```

The script creates a single-task Databricks Job that:

1. Runs `01_enrich_artists` on serverless compute
2. Cron-triggers nightly at midnight Pacific (`0 0 8 * * ?` UTC)
3. Times out after 30 minutes
4. Pulls `ROSTR_USERNAME / ROSTR_PASSWORD / GOOGLE_*` from a Databricks **secret scope**, not `.env`

Before scheduling you'll want a real Sheets auth mode for unattended runs:

1. Create a GCP service account, enable the **Sheets API** for its project.
2. Generate a JSON key, upload to a Databricks secret scope:
   ```bash
   databricks secrets create-scope rostr_demo
   databricks secrets put-secret rostr_demo google_sa_json --string-value "$(cat sa.json)"
   databricks secrets put-secret rostr_demo rostr_username --string-value '...'
   databricks secrets put-secret rostr_demo rostr_password --string-value '...'
   ```
3. Share the Google Sheet with the service-account email (Editor permission).
4. The notebook reads from `dbutils.secrets` when `GOOGLE_AUTH_MODE=service`.

---

## Demo script (≤10 minutes)

1. Show the empty sheet.
2. Open `.env` — point out it's just username/password, no API key magic.
3. Run `00_verify_connection.ipynb` → green checks; show the rostr probe finding "Olivia Rodrigo / WME / Kirk Sommer / ksommer@wmeagency.com".
4. Run `01_enrich_artists.ipynb` → watch the log scrape three artists; refresh the sheet to show populated cells.
5. Re-run notebook 01 → demonstrate idempotency (only re-tries rows still missing data).
6. Show `create_job.py`, scheduling, and the secret-scope handoff.
7. *(Optional)* Flip `PERSIST_TO_UC=true`, re-run, show the Delta history table in Catalog Explorer for the audit story.
