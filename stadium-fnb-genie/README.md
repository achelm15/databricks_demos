# Stadium F&B Genie Demo

Natural-language analytics on synthetic sports-venue concessions data — built for a Genie UI walkthrough.

**Hosted on:** `e2-demo-field-eng.cloud.databricks.com`
**Catalog/schema:** `alexander_booth.stadium_fnb_demo`
**Customer name:** intentionally hidden. Nothing in the catalog, schema, table, or column names references the customer.

## What's in here

| File | What it does |
|---|---|
| `DEMO.md` | Architecture, scale, brand notes. |
| `TASKS.md` | Build checklist. |
| `generate_data.py` | Generates all 10 tables and writes to UC via Databricks Connect. |
| `add_comments.py` | Adds table/column comments and PK/FK constraints. |
| `rescale.py` | Bumps revenue/inventory volume 10x so per-cap and labor% sit in realistic ranges. |
| `genie_setup.md` | **Paste-ready Genie config** — title, description, general instructions, sample questions, 7 trusted SQL examples. |

## Tables (in `alexander_booth.stadium_fnb_demo`)

| Table | Rows | Purpose |
|---|---|---|
| `venues` | 10 | Stadiums / arenas. League type, capacity, climate zone. |
| `events` | 400 | Games/concerts with attendance + weather + weekend flag. |
| `menu_items` | 60 | SKUs with retail price, unit cost, premium flag. |
| `concession_stands` | 120 | POS locations (general/premium/specialty/bar). |
| `stand_menu` | 1,989 | Which items each stand offers. |
| `transactions` | 319,563 | Receipt header. |
| `transaction_items` | 659,546 | Line items. |
| `staff` | 1,200 | Employees by role. |
| `labor_shifts` | 24,947 | Staff scheduled per event with labor cost. |
| `inventory_movements` | 22,728 | Per-event opening/sold/waste/closing qty for top SKUs. |

Time range: 2024-04-01 → 2025-09-30. Built-in correlations: heat boosts beer per-cap, weekends boost attendance, rain suppresses sales, fresh items have higher waste rates.

## Demo day flow

1. **Create the Genie space** (one-time, ~60 seconds):
   - Open `genie_setup.md` and follow Section 1.
   - Title: `Stadium F&B Operations`
   - Add all 10 tables from `alexander_booth.stadium_fnb_demo`
2. **Paste in the curated content** (Sections 2-4 of `genie_setup.md`):
   - General instructions (glossary, join hints, per-cap convention)
   - 15 sample questions
   - 7 trusted SQL examples (per-cap, labor%, waste%, weather-vs-beer, top stands, monthly trend, items-per-fan)
3. **Walk the customer through the UI**, asking the sample questions live. Genie will use the trusted SQL examples as canonical patterns for unfamiliar phrasings.

## What customer-relevant insights are baked in

When the customer asks these out loud, Genie should reveal:

- **Per-cap by venue:** Coastline Field (hot, NFL-style) leads at $6.38; Summit Center (cold, NBA-style) trails at $5.41.
- **Beer vs. temperature:** Per-cap beer units climb from 0.69 at <45°F → 1.52 at 85°F+. Clean monotonic upward curve.
- **Waste by category:** burger 6.0% > hot_dog 5.1% > pizza 4.0% > kids 2.6% ... beer 0%. Fresh items waste more — actionable.
- **Labor%:** Higher at arenas (NHL/NBA, lower attendance) at ~10-14% vs. NFL stadiums at 3-5%.
- **Monthly revenue trend:** Visible seasonality — peak in May (32 events), trough in winter months for outdoor venues.

## Rebuilding from scratch

```bash
source ~/miniconda3/etc/profile.d/conda.sh && conda activate demo-env
DATABRICKS_CONFIG_PROFILE=DEFAULT python generate_data.py
DATABRICKS_CONFIG_PROFILE=DEFAULT python add_comments.py
DATABRICKS_CONFIG_PROFILE=DEFAULT python rescale.py
```

Then follow `genie_setup.md` for the UI side.
