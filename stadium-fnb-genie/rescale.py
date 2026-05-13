"""
Rescale transaction and inventory volume 10x so per-cap and labor% sit in
realistic concessions ranges (per-cap ~$6-8, labor% ~10-15%). The original
generator under-sized the per-event transaction count. Re-doing via Connect
DML so we don't have to regenerate from scratch.
"""
from databricks.connect import DatabricksSession

C = "alexander_booth.stadium_fnb_demo"
spark = DatabricksSession.builder.serverless().getOrCreate()

statements = [
    # Multiply transaction_items by 10
    f"""
    INSERT OVERWRITE TABLE {C}.transaction_items
    SELECT transaction_id, item_id, quantity * 10 AS quantity,
           unit_price_usd, ROUND(line_total_usd * 10, 2) AS line_total_usd
    FROM {C}.transaction_items
    """,
    # Multiply transactions totals by 10, recompute item_count from items
    f"""
    INSERT OVERWRITE TABLE {C}.transactions
    SELECT t.transaction_id, t.stand_id, t.event_id, t.transaction_ts,
           ROUND(t.total_usd * 10, 2) AS total_usd,
           t.payment_method, t.item_count * 10 AS item_count
    FROM {C}.transactions t
    """,
    # Multiply inventory quantities by 10
    f"""
    INSERT OVERWRITE TABLE {C}.inventory_movements
    SELECT venue_id, event_id, item_id,
           opening_qty * 10 AS opening_qty,
           sold_qty * 10    AS sold_qty,
           waste_qty * 10   AS waste_qty,
           closing_qty * 10 AS closing_qty
    FROM {C}.inventory_movements
    """,
]

for s in statements:
    print("Running...", s.split()[2], s.split()[4])
    spark.sql(s)

# Sanity check
print("\n--- Verification ---")
print(spark.sql(f"""
  SELECT v.venue_name,
         ROUND(AVG(rev.r / e.attendance), 2) AS per_cap_usd,
         ROUND(AVG(lab.l / NULLIF(rev.r,0)), 3) AS labor_pct,
         COUNT(*) AS events
  FROM {C}.events e
  JOIN {C}.venues v USING (venue_id)
  JOIN (SELECT event_id, SUM(total_usd) AS r FROM {C}.transactions GROUP BY event_id) rev USING (event_id)
  JOIN (SELECT event_id, SUM(labor_cost_usd) AS l FROM {C}.labor_shifts GROUP BY event_id) lab USING (event_id)
  GROUP BY v.venue_name ORDER BY per_cap_usd DESC
""").toPandas().to_string())
spark.stop()
