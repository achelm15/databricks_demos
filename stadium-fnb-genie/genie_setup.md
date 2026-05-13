# Genie Room Setup — Paste-Ready Content

The Genie space CREATE API is gated. Create the space in the UI (60 seconds), then paste each block below into the matching tab.

## 1. Create the space

1. Open https://e2-demo-field-eng.cloud.databricks.com/
2. Left nav → **Genie** → **New** → **Genie space**
3. Fill in:
   - **Title:** `Stadium F&B Operations`
   - **Description:** `Natural-language analytics for sports-venue food & beverage concessions — sales, attendance, weather, menu mix, labor cost, and waste.`
   - **SQL warehouse:** `Shared Unity Catalog Serverless` (or any running serverless)
   - **Data:** click **Add tables**, then select all 10 tables in `alexander_booth.stadium_fnb_demo`
4. Click **Save**.

## 2. Settings → Instructions → General Instructions

Paste this block:

```
This space answers business questions about sports-venue food & beverage concessions across 10 venues. Tables include venues, events (games/concerts with attendance + weather), concession_stands, menu_items, transactions (receipts), transaction_items (line items), staff, labor_shifts, and inventory_movements.

Glossary and conventions:
- "Revenue" or "concession revenue" = SUM(transactions.total_usd). For per-item revenue use SUM(transaction_items.line_total_usd).
- "Per-cap" = revenue / attendance. Always compute at the event grain, then average. Never divide total revenue by total attendance across events.
- "Items per fan" or "units per attendee" = SUM(transaction_items.quantity) / events.attendance. Use this as the engagement metric, not a "share of buyers" rate (each receipt covers multiple fans).
- "Average ticket" = AVG(transactions.total_usd).
- "Margin per item" = price_usd - unit_cost_usd from menu_items.
- "Waste rate" = waste_qty / (sold_qty + waste_qty) from inventory_movements.
- "Labor %" = SUM(labor_shifts.labor_cost_usd) / SUM(transactions.total_usd) at the event grain.
- "Last season" without qualification = the 2025 season (2025-04-01 to 2025-09-30). "This season" = same window.
- "Weekend" = is_weekend = 1 (Sat/Sun).
- "Premium items" = menu_items.is_premium = 1. "Premium stands" = concession_stands.stand_type = 'premium'.
- League type is one of: MLB-style, NFL-style, NBA-style, NHL-style, multi-use. These are stylized labels, not real leagues.
- Weather condition is categorical: Hot, Warm, Mild, Cold, Light Rain, Rainy. Temperature is in degrees Fahrenheit.
- Always show currency values rounded to two decimals and prefixed with "$" in answers.
- When the user asks "which X is best/worst", return the top 5 (or bottom 5) sorted, not just one row, unless they say "the single best".
- When comparing across venues, normalize by attendance (per-cap) unless the user explicitly asks for totals.

Join hints:
- transactions → events on event_id (gets date, weather, attendance, weekend).
- transactions → concession_stands on stand_id (gets stand_type, venue_id).
- transaction_items → transactions on transaction_id, then events for context.
- transaction_items → menu_items on item_id (gets category, price, cost, premium).
- labor_shifts → events on event_id; labor cost per event = SUM(labor_shifts.labor_cost_usd) grouped by event_id.
- inventory_movements has both venue_id and event_id; aggregate by item_id or category for waste analysis.
```

## 3. Sample questions

In Settings → **Sample questions**, add these one at a time:

```
Which venue had the highest total concession revenue last season?
What's the average per-cap spend by venue?
How does rain affect beer sales?
Which menu items have the worst waste rate?
Top 10 best-selling premium items
Labor cost as a percent of revenue per event, ranked
Which concession stand has the highest average ticket?
Compare weekend vs weekday revenue per event
Which payment method has the highest average ticket size?
Show me monthly revenue trend
Items per fan at Lakeside Stadium vs Desert Sky Ballpark
Top selling beer at hot weather games (over 85 degrees)
Hourly revenue curve at sold-out events
Which vendor partner runs the highest-margin stands?
Show me waste rate by item category
```

## 4. Trusted SQL Examples

In Settings → **Instructions** → **SQL** (or "Trusted assets"), add each of these as a named example. Genie uses these as canonical patterns for similar questions.

### Example 1 — Per-cap spend by venue

**Question template:** "Per-cap spend by venue", "average per-cap by stadium", "spend per attendee"

```sql
WITH event_perf AS (
  SELECT
    e.venue_id,
    e.event_id,
    e.attendance,
    SUM(t.total_usd) AS event_revenue
  FROM alexander_booth.stadium_fnb_demo.events e
  JOIN alexander_booth.stadium_fnb_demo.transactions t USING (event_id)
  GROUP BY e.venue_id, e.event_id, e.attendance
)
SELECT
  v.venue_name,
  AVG(ep.event_revenue / ep.attendance) AS avg_per_cap_usd,
  COUNT(*) AS events
FROM event_perf ep
JOIN alexander_booth.stadium_fnb_demo.venues v USING (venue_id)
GROUP BY v.venue_name
ORDER BY avg_per_cap_usd DESC;
```

### Example 2 — Labor % per event

**Question template:** "Labor cost as a percent of revenue per event", "labor ratio by game"

```sql
WITH revenue AS (
  SELECT event_id, SUM(total_usd) AS rev FROM alexander_booth.stadium_fnb_demo.transactions GROUP BY event_id
),
labor AS (
  SELECT event_id, SUM(labor_cost_usd) AS lc FROM alexander_booth.stadium_fnb_demo.labor_shifts GROUP BY event_id
)
SELECT
  e.event_id,
  e.event_date,
  v.venue_name,
  r.rev          AS revenue_usd,
  l.lc           AS labor_cost_usd,
  l.lc / r.rev   AS labor_pct
FROM alexander_booth.stadium_fnb_demo.events e
JOIN alexander_booth.stadium_fnb_demo.venues v USING (venue_id)
JOIN revenue r USING (event_id)
JOIN labor   l USING (event_id)
ORDER BY labor_pct DESC;
```

### Example 3 — Waste rate by category

**Question template:** "Waste rate by category", "which items waste the most"

```sql
SELECT
  m.category,
  SUM(i.waste_qty) AS total_waste,
  SUM(i.sold_qty)  AS total_sold,
  SUM(i.waste_qty) * 1.0 / NULLIF(SUM(i.waste_qty + i.sold_qty), 0) AS waste_rate
FROM alexander_booth.stadium_fnb_demo.inventory_movements i
JOIN alexander_booth.stadium_fnb_demo.menu_items m USING (item_id)
GROUP BY m.category
ORDER BY waste_rate DESC;
```

### Example 4 — Weather effect on beer sales

**Question template:** "How does weather affect beer sales", "beer revenue by temperature bucket"

```sql
WITH beer_sales AS (
  SELECT
    t.event_id,
    SUM(ti.line_total_usd) AS beer_revenue,
    COUNT(*)               AS beer_units
  FROM alexander_booth.stadium_fnb_demo.transaction_items ti
  JOIN alexander_booth.stadium_fnb_demo.menu_items m USING (item_id)
  JOIN alexander_booth.stadium_fnb_demo.transactions t USING (transaction_id)
  WHERE m.category = 'beer'
  GROUP BY t.event_id
)
SELECT
  CASE
    WHEN e.temp_f >= 85 THEN '85F+'
    WHEN e.temp_f >= 75 THEN '75-84F'
    WHEN e.temp_f >= 60 THEN '60-74F'
    WHEN e.temp_f >= 45 THEN '45-59F'
    ELSE '<45F'
  END AS temp_bucket,
  e.weather_condition,
  COUNT(*)                         AS events,
  AVG(bs.beer_revenue / e.attendance) AS per_cap_beer_rev,
  SUM(bs.beer_units)                  AS total_beer_units
FROM alexander_booth.stadium_fnb_demo.events e
JOIN beer_sales bs USING (event_id)
GROUP BY temp_bucket, e.weather_condition
ORDER BY temp_bucket, per_cap_beer_rev DESC;
```

### Example 5 — Top stands by average ticket

**Question template:** "Highest average ticket stand", "best stands by spend per transaction"

```sql
SELECT
  v.venue_name,
  cs.stand_name,
  cs.stand_type,
  AVG(t.total_usd) AS avg_ticket_usd,
  COUNT(*)         AS transactions
FROM alexander_booth.stadium_fnb_demo.transactions t
JOIN alexander_booth.stadium_fnb_demo.concession_stands cs USING (stand_id)
JOIN alexander_booth.stadium_fnb_demo.venues v ON v.venue_id = cs.venue_id
GROUP BY v.venue_name, cs.stand_name, cs.stand_type
HAVING COUNT(*) >= 100
ORDER BY avg_ticket_usd DESC
LIMIT 25;
```

### Example 6 — Monthly revenue trend

**Question template:** "Revenue trend by month", "how is revenue changing over time"

```sql
SELECT
  DATE_TRUNC('month', e.event_date) AS month,
  SUM(t.total_usd) AS revenue_usd,
  COUNT(DISTINCT e.event_id) AS events,
  SUM(e.attendance) AS attendance
FROM alexander_booth.stadium_fnb_demo.events e
JOIN alexander_booth.stadium_fnb_demo.transactions t USING (event_id)
GROUP BY DATE_TRUNC('month', e.event_date)
ORDER BY month;
```

### Example 7 — Items per fan by venue

**Question template:** "Items per fan by venue", "units per attendee", "engagement by venue"

```sql
SELECT
  v.venue_name,
  ROUND(SUM(ti.quantity) * 1.0 / SUM(e.attendance), 3) AS items_per_fan,
  SUM(ti.quantity)  AS units_sold,
  SUM(e.attendance) AS attendance
FROM alexander_booth.stadium_fnb_demo.events e
JOIN alexander_booth.stadium_fnb_demo.venues v        USING (venue_id)
JOIN alexander_booth.stadium_fnb_demo.transactions t  USING (event_id)
JOIN alexander_booth.stadium_fnb_demo.transaction_items ti USING (transaction_id)
GROUP BY v.venue_name
ORDER BY items_per_fan DESC;
```

## 5. Verify

After saving, run the first sample question. If Genie returns clean SQL using the joins above, you're set.
