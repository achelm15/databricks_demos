"""
Create the Stadium F&B Operations Genie space via the public REST API.

Run:
    DATABRICKS_CONFIG_PROFILE=DEFAULT python create_genie_space.py
"""
import json
import os
from databricks.sdk import WorkspaceClient

UC_CATALOG = "alexander_booth"
UC_SCHEMA  = "stadium_fnb_demo"
SQL_WAREHOUSE_ID = "4b9b953939869799"  # Shared Unity Catalog Serverless
GENIE_TITLE = "Stadium F&B Operations"
GENIE_DESCRIPTION = (
    "Natural-language analytics for sports-venue food & beverage concessions — "
    "sales, attendance, weather, menu mix, labor cost, and waste."
)

w = WorkspaceClient(profile=os.getenv("DATABRICKS_CONFIG_PROFILE", "DEFAULT"))

S = f"{UC_CATALOG}.{UC_SCHEMA}"
TABLES = sorted([
    f"{S}.concession_stands",
    f"{S}.events",
    f"{S}.inventory_movements",
    f"{S}.labor_shifts",
    f"{S}.menu_items",
    f"{S}.staff",
    f"{S}.stand_menu",
    f"{S}.transaction_items",
    f"{S}.transactions",
    f"{S}.venues",
])

INSTRUCTIONS = [
    "This space answers business questions about sports-venue food & beverage concessions across 10 venues. Tables include venues, events (games/concerts with attendance + weather), concession_stands, menu_items, transactions (receipts), transaction_items (line items), staff, labor_shifts, and inventory_movements.",
    "Revenue = SUM(transactions.total_usd). For per-item revenue use SUM(transaction_items.line_total_usd).",
    "Per-cap = revenue / attendance, always computed at the event grain and then averaged. Never divide total revenue by total attendance across events.",
    "Items per fan / units per attendee = SUM(transaction_items.quantity) / events.attendance. Use this as the engagement metric — each receipt covers multiple fans so a 'share of buyers' rate is misleading.",
    "Average ticket = AVG(transactions.total_usd).",
    "Margin per item = price_usd - unit_cost_usd from menu_items.",
    "Waste rate = waste_qty / (sold_qty + waste_qty) from inventory_movements.",
    "Labor % = SUM(labor_shifts.labor_cost_usd) / SUM(transactions.total_usd) at the event grain.",
    "Last season without qualification = the 2025 season (2025-04-01 to 2025-09-30). This season = same window.",
    "Weekend = is_weekend = 1 (Saturday/Sunday). Weekday = 0.",
    "Premium items = menu_items.is_premium = 1. Premium stands = concession_stands.stand_type = 'premium'.",
    "League type is one of: MLB-style, NFL-style, NBA-style, NHL-style, multi-use. These are stylized labels, not real leagues.",
    "Weather condition is categorical: Hot, Warm, Mild, Cold, Light Rain, Rainy. Temperature is in degrees Fahrenheit.",
    "Always show currency values rounded to two decimals and prefixed with $ in answers.",
    "When the user asks 'which X is best/worst', return the top 5 (or bottom 5) sorted, not just one row, unless they say 'the single best'.",
    "When comparing across venues, normalize by attendance (per-cap) unless the user explicitly asks for totals.",
    "Join transactions → events on event_id (gets date, weather, attendance, weekend flag).",
    "Join transactions → concession_stands on stand_id (gets stand_type, vendor_partner, venue_id).",
    "Join transaction_items → transactions on transaction_id, then events for context.",
    "Join transaction_items → menu_items on item_id (gets category, price, cost, premium flag).",
    "labor_shifts → events on event_id; labor cost per event = SUM(labor_shifts.labor_cost_usd) grouped by event_id.",
    "inventory_movements has both venue_id and event_id; aggregate by item_id or menu_items.category for waste analysis.",
]

genie_config = {
    "version": 2,
    "data_sources": {"tables": [{"identifier": t} for t in TABLES]},
    "instructions": {
        "text_instructions": [{"content": INSTRUCTIONS}]
    },
}
serialized = json.dumps(genie_config)
print(f"Tables: {len(TABLES)} | Instructions chars: {len(serialized):,}")

current_user = w.current_user.me()
parent_path  = f"/Workspace/Users/{current_user.user_name}"

# Find or create
existing_id = None
try:
    resp = w.api_client.do("GET", "/api/2.0/genie/spaces")
    for s in resp.get("spaces", []):
        if s.get("title", "").startswith(GENIE_TITLE):
            existing_id = s["space_id"]
            print(f"Reusing existing Genie space: {existing_id}")
            break
except Exception:
    pass

if existing_id:
    space_id = existing_id
else:
    response = w.api_client.do(
        "POST", "/api/2.0/genie/spaces",
        body={
            "warehouse_id":     SQL_WAREHOUSE_ID,
            "title":            GENIE_TITLE,
            "description":      GENIE_DESCRIPTION,
            "serialized_space": serialized,
            "parent_path":      parent_path,
        },
    )
    space_id = response.get("space_id", response.get("id", "unknown"))
    print(f"Genie space created: {space_id}")

host = "https://e2-demo-field-eng.cloud.databricks.com"
print(f"\nTitle: {GENIE_TITLE}")
print(f"Open:  {host}/genie/rooms/{space_id}")
