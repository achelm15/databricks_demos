"""
Stadium F&B Genie Demo — synthetic data generator.

Generates 10 tables of sports-venue concessions data and writes them to:
    alexander_booth.stadium_fnb_demo.*

Run:
    uv run --with polars --with numpy --with "databricks-connect>=16.4,<17.0" generate_data.py

Plan summary:
    venues (10), events (400), concession_stands (120), menu_items (60),
    stand_menu (~1.8K), transactions (~600K), transaction_items (~1.4M),
    staff (1.2K), labor_shifts (~20K), inventory_movements (~50K).
    Time range: 2024-04-01 to 2025-09-30. Seed: 42.
"""

from __future__ import annotations

import numpy as np
import polars as pl
from databricks.connect import DatabricksSession

CATALOG = "alexander_booth"
SCHEMA = "stadium_fnb_demo"
SEED = 42

rng = np.random.default_rng(SEED)

# -------------------------------------------------------------------------
# Static reference data
# -------------------------------------------------------------------------

VENUES = [
    # (name, city, league_type, capacity, climate_zone)
    ("Lakeside Stadium",       "Buffalo",      "MLB-style",  41_500, "cold"),
    ("Riverbend Park",         "Cincinnati",   "MLB-style",  43_000, "temperate"),
    ("Harbor Arena",           "Boston",       "NHL-style",  17_800, "cold"),
    ("Summit Center",          "Denver",       "NBA-style",  19_500, "cold"),
    ("Coastline Field",        "Tampa",        "NFL-style",  65_000, "hot"),
    ("Northstar Coliseum",     "Minneapolis",  "NFL-style",  66_500, "cold"),
    ("Desert Sky Ballpark",    "Phoenix",      "MLB-style",  48_000, "hot"),
    ("Crescent Garden",        "New Orleans",  "NBA-style",  18_200, "hot"),
    ("Ironworks Arena",        "Pittsburgh",   "NHL-style",  18_400, "cold"),
    ("Bayfront Pavilion",      "San Diego",    "multi-use",  42_000, "temperate"),
]

# Curated menu — 60 items across 8 categories
MENU = [
    # (name, category, price, cost, is_premium)
    # Beer (10)
    ("Domestic Draft 16oz",      "beer", 10.50, 2.10, 0),
    ("Premium Draft 16oz",       "beer", 12.50, 2.80, 0),
    ("Craft IPA 16oz",           "beer", 14.00, 3.20, 1),
    ("Light Lager 16oz",         "beer", 10.00, 1.95, 0),
    ("Local Pilsner 16oz",       "beer", 13.50, 3.00, 1),
    ("Hard Seltzer",             "beer", 11.50, 2.40, 0),
    ("Stadium Stout 16oz",       "beer", 13.00, 2.95, 1),
    ("Imported Pilsner",         "beer", 12.50, 2.85, 0),
    ("Tall Boy Domestic 24oz",   "beer", 14.00, 2.60, 0),
    ("Hard Cider",               "beer", 11.00, 2.50, 0),
    # Soft drinks (8)
    ("Fountain Cola 22oz",       "soft_drink",  6.50, 0.55, 0),
    ("Fountain Diet Cola 22oz",  "soft_drink",  6.50, 0.55, 0),
    ("Lemon-Lime 22oz",          "soft_drink",  6.50, 0.55, 0),
    ("Bottled Water 20oz",       "soft_drink",  5.50, 0.40, 0),
    ("Sports Drink 20oz",        "soft_drink",  6.50, 0.95, 0),
    ("Iced Tea 22oz",            "soft_drink",  6.00, 0.45, 0),
    ("Hot Coffee 12oz",          "soft_drink",  5.50, 0.35, 0),
    ("Hot Chocolate 12oz",       "soft_drink",  6.00, 0.55, 0),
    # Hot dogs / sausages (8)
    ("Classic Hot Dog",          "hot_dog", 7.50, 1.10, 0),
    ("Foot-Long Hot Dog",        "hot_dog", 9.50, 1.60, 0),
    ("Bratwurst",                "hot_dog", 10.00, 1.95, 0),
    ("Italian Sausage",          "hot_dog", 10.50, 2.05, 0),
    ("Chili Dog",                "hot_dog", 9.00, 1.65, 0),
    ("Chicago Dog",              "hot_dog", 9.50, 1.70, 0),
    ("Veggie Dog",               "hot_dog", 8.50, 1.85, 0),
    ("Polish Sausage",           "hot_dog", 10.00, 1.90, 0),
    # Burgers / sandwiches (6)
    ("Stadium Cheeseburger",     "burger", 12.50, 2.40, 0),
    ("Double Cheeseburger",      "burger", 15.00, 3.40, 0),
    ("Chicken Sandwich",         "burger", 12.00, 2.20, 0),
    ("Crispy Chicken Tenders",   "burger", 11.50, 2.10, 0),
    ("Pulled Pork Sandwich",     "burger", 13.50, 2.80, 0),
    ("Veggie Burger",            "burger", 11.50, 2.40, 0),
    # Pizza (4)
    ("Cheese Pizza Slice",       "pizza", 8.50, 1.20, 0),
    ("Pepperoni Pizza Slice",    "pizza", 9.50, 1.40, 0),
    ("Personal Pepperoni Pie",   "pizza", 15.00, 2.85, 0),
    ("Personal Cheese Pie",      "pizza", 14.00, 2.60, 0),
    # Snacks (10)
    ("Soft Pretzel",             "snack", 7.50, 0.75, 0),
    ("Pretzel Bites & Cheese",   "snack", 9.00, 1.25, 0),
    ("Popcorn (Regular)",        "snack", 7.00, 0.55, 0),
    ("Popcorn (Souvenir Bucket)", "snack", 12.00, 1.45, 0),
    ("Nachos with Cheese",       "snack", 8.50, 1.15, 0),
    ("Loaded Nachos",            "snack", 13.50, 2.35, 0),
    ("Peanuts",                  "snack", 6.50, 0.60, 0),
    ("Cracker Jack",             "snack", 7.00, 0.85, 0),
    ("Cotton Candy",             "snack", 7.50, 0.65, 0),
    ("Churros",                  "snack", 8.00, 1.10, 0),
    # Premium / specialty (8)
    ("Premium Brisket Plate",    "premium", 24.00, 6.50, 1),
    ("Lobster Roll",             "premium", 28.00, 9.20, 1),
    ("Premium Burger Stack",     "premium", 22.00, 5.40, 1),
    ("Smoked Wings (12pc)",      "premium", 21.00, 4.95, 1),
    ("Carnitas Tacos (3)",       "premium", 18.00, 3.85, 1),
    ("Sushi Combo",              "premium", 24.00, 7.20, 1),
    ("Craft Cocktail",           "premium", 16.00, 3.60, 1),
    ("Wine 6oz",                 "premium", 14.00, 3.20, 1),
    # Kids (6)
    ("Kids Hot Dog Meal",        "kids",  9.00, 1.45, 0),
    ("Kids Chicken Tender Meal", "kids", 10.00, 1.85, 0),
    ("Kids Pizza Meal",          "kids",  9.50, 1.55, 0),
    ("Kids Mac & Cheese",        "kids",  8.50, 1.20, 0),
    ("Kids Juice Box",           "kids",  4.00, 0.30, 0),
    ("Kids Combo Souvenir Cup",  "kids", 11.00, 1.90, 0),
]

VENDOR_PARTNERS = ["Centerline Hospitality", "Stadium Eats Group", "Game Day Foods",
                   "Coast2Coast Concessions", "Apex Venue Partners"]
STAND_TYPES = ["general", "premium", "specialty", "bar"]
STAND_TYPE_WEIGHTS = np.array([0.55, 0.15, 0.20, 0.10])
CONCOURSE_LEVELS = ["Field Level", "100 Level", "200 Level", "300 Level", "Club Level", "Suite Level"]
STAFF_ROLES = ["Cashier", "Cook", "Server", "Bartender", "Stand Lead", "Manager"]
PAYMENT_METHODS = ["Mobile", "Credit Card", "Cash", "Loyalty App"]
PAYMENT_WEIGHTS = np.array([0.30, 0.50, 0.10, 0.10])

# -------------------------------------------------------------------------
# 1. Venues
# -------------------------------------------------------------------------
print("Generating venues...")
venues = pl.DataFrame({
    "venue_id": [f"V{i+1:03d}" for i in range(len(VENUES))],
    "venue_name":  [v[0] for v in VENUES],
    "city":        [v[1] for v in VENUES],
    "league_type": [v[2] for v in VENUES],
    "capacity":    [v[3] for v in VENUES],
    "climate_zone":[v[4] for v in VENUES],
    "opened_year": [int(x) for x in rng.integers(1985, 2020, size=len(VENUES))],
})

# -------------------------------------------------------------------------
# 2. Events
# -------------------------------------------------------------------------
print("Generating events...")
N_EVENTS = 400
DATE_START = np.datetime64("2024-04-01")
DATE_END   = np.datetime64("2025-09-30")
SPAN = (DATE_END - DATE_START).astype(int)  # days

event_venue_idx = rng.integers(0, len(VENUES), size=N_EVENTS)
event_date_offsets = rng.integers(0, SPAN + 1, size=N_EVENTS)
event_dates = DATE_START + event_date_offsets.astype("timedelta64[D]")

# event type by league
event_types = []
for vi in event_venue_idx:
    lt = VENUES[vi][2]
    if lt == "MLB-style":   event_types.append(rng.choice(["Regular Season Game", "Concert"], p=[0.92, 0.08]))
    elif lt == "NFL-style": event_types.append(rng.choice(["Regular Season Game", "Concert", "Playoff Game"], p=[0.80, 0.15, 0.05]))
    elif lt == "NBA-style": event_types.append(rng.choice(["Regular Season Game", "Concert"], p=[0.85, 0.15]))
    elif lt == "NHL-style": event_types.append(rng.choice(["Regular Season Game", "Concert"], p=[0.80, 0.20]))
    else:                   event_types.append(rng.choice(["Concert", "Special Event"], p=[0.70, 0.30]))

# weather, attendance, weekend - all interrelated
weekday = ((event_dates.astype("datetime64[D]").astype(int)) + 4) % 7  # 0=Mon...
is_weekend = (weekday >= 5).astype(int)
month = event_dates.astype("datetime64[M]").astype(int) % 12 + 1

# Base attendance from venue capacity (60-100%), bumped on weekends + by event type
capacities = np.array([VENUES[i][3] for i in event_venue_idx])
attendance_pct = rng.uniform(0.55, 0.92, size=N_EVENTS)
attendance_pct += 0.05 * is_weekend
attendance_pct += np.where(np.array(event_types) == "Playoff Game", 0.12, 0)
attendance_pct += np.where(np.array(event_types) == "Concert", 0.05, 0)
attendance_pct = np.clip(attendance_pct, 0.45, 1.00)
attendance = (capacities * attendance_pct).astype(int)
sold_out = (attendance_pct >= 0.97).astype(int)

# Temperature: climate-zone-driven, with seasonal sin wave
climate_offset = np.array(
    [{"cold": -10, "temperate": 0, "hot": 12}[VENUES[i][4]] for i in event_venue_idx]
)
seasonal = 25 * np.sin(2 * np.pi * (month - 4) / 12)  # peak in July
temp_f = 65 + seasonal + climate_offset + rng.normal(0, 6, size=N_EVENTS)
temp_f = np.round(temp_f, 1)

# Precipitation: rare, biased by climate (cold zones get more rain in spring)
precip = np.where(rng.random(N_EVENTS) < 0.18,
                  rng.gamma(1.5, 0.4, size=N_EVENTS), 0.0)
precip = np.round(precip, 2)

# Weather condition label
weather_condition = np.where(precip > 0.5, "Rainy",
                     np.where(precip > 0.05, "Light Rain",
                     np.where(temp_f > 88, "Hot",
                     np.where(temp_f < 40, "Cold",
                     np.where(temp_f > 75, "Warm", "Mild")))))

events = pl.DataFrame({
    "event_id":   [f"E{i+1:05d}" for i in range(N_EVENTS)],
    "venue_id":   [f"V{int(i)+1:03d}" for i in event_venue_idx],
    "event_date": event_dates.astype("datetime64[D]").astype("datetime64[ns]"),
    "event_type": event_types,
    "home_team":  ["Home Club"] * N_EVENTS,
    "opponent":   [f"Visitor {i+1}" for i in rng.integers(1, 30, size=N_EVENTS)],
    "attendance": attendance.tolist(),
    "sold_out_flag": sold_out.tolist(),
    "temp_f": temp_f.tolist(),
    "precipitation_in": precip.tolist(),
    "weather_condition": weather_condition.tolist(),
    "is_weekend": is_weekend.tolist(),
}).sort("event_date")

# -------------------------------------------------------------------------
# 3. Menu items
# -------------------------------------------------------------------------
print("Generating menu_items...")
menu_items = pl.DataFrame({
    "item_id":      [f"M{i+1:03d}" for i in range(len(MENU))],
    "item_name":    [m[0] for m in MENU],
    "category":     [m[1] for m in MENU],
    "price_usd":    [m[2] for m in MENU],
    "unit_cost_usd":[m[3] for m in MENU],
    "is_premium":   [m[4] for m in MENU],
})

# -------------------------------------------------------------------------
# 4. Concession stands
# -------------------------------------------------------------------------
print("Generating concession_stands...")
STANDS_PER_VENUE = 12
stand_rows = []
for vi, (vname, city, lt, cap, climate) in enumerate(VENUES):
    for s in range(STANDS_PER_VENUE):
        stype = rng.choice(STAND_TYPES, p=STAND_TYPE_WEIGHTS)
        level = rng.choice(CONCOURSE_LEVELS)
        if stype == "bar":
            sname = f"{level} Bar #{s+1}"
        elif stype == "premium":
            sname = f"Premium Club Stand #{s+1}"
        elif stype == "specialty":
            sname = f"Specialty Eats #{s+1}"
        else:
            sname = f"Stand #{s+1}"
        stand_rows.append({
            "stand_id": f"S{vi+1:02d}-{s+1:02d}",
            "venue_id": f"V{vi+1:03d}",
            "stand_name": sname,
            "concourse_level": level,
            "stand_type": stype,
            "vendor_partner": rng.choice(VENDOR_PARTNERS),
        })
concession_stands = pl.DataFrame(stand_rows)

# -------------------------------------------------------------------------
# 5. Stand menu
# -------------------------------------------------------------------------
print("Generating stand_menu...")
item_categories = np.array([m[1] for m in MENU])
item_is_premium = np.array([m[4] for m in MENU])

stand_menu_rows = []
for sr in stand_rows:
    stype = sr["stand_type"]
    if stype == "bar":
        # Bars: heavy beer + premium drinks + light food
        mask = (item_categories == "beer") | (item_categories == "soft_drink") | (item_categories == "premium")
        eligible = np.where(mask)[0]
    elif stype == "premium":
        # Premium stands: premium items + better food + drinks
        mask = (item_is_premium == 1) | (item_categories == "beer") | (item_categories == "burger") | (item_categories == "soft_drink")
        eligible = np.where(mask)[0]
    elif stype == "specialty":
        # Specialty: focused 2-3 categories, randomly chosen
        focus = rng.choice(["hot_dog", "burger", "pizza", "snack"], size=2, replace=False)
        mask = np.isin(item_categories, list(focus) + ["soft_drink"])
        eligible = np.where(mask)[0]
    else:
        # General: full mix, exclude premium
        mask = (item_is_premium == 0)
        eligible = np.where(mask)[0]

    # 10-22 items per stand
    n_items = rng.integers(10, 23)
    chosen = rng.choice(eligible, size=min(n_items, len(eligible)), replace=False)
    for ci in chosen:
        stand_menu_rows.append({
            "stand_id": sr["stand_id"],
            "item_id":  f"M{ci+1:03d}",
            "available_flag": 1,
        })
stand_menu = pl.DataFrame(stand_menu_rows)

# -------------------------------------------------------------------------
# 6. Transactions + 7. Transaction items
# -------------------------------------------------------------------------
print("Generating transactions and transaction_items...")

# Build stand_id -> venue_id and stand_id -> stand_type maps
stand_lookup = {sr["stand_id"]: (sr["venue_id"], sr["stand_type"]) for sr in stand_rows}
# Build venue_id -> [stand_id] mapping
venue_stands = {}
for sr in stand_rows:
    venue_stands.setdefault(sr["venue_id"], []).append(sr["stand_id"])
# stand_id -> [item indexes]
stand_items_map = {}
for r in stand_menu_rows:
    stand_items_map.setdefault(r["stand_id"], []).append(int(r["item_id"][1:]) - 1)

menu_price = np.array([m[2] for m in MENU])
menu_cost  = np.array([m[3] for m in MENU])

# We'll generate per-event txns then concatenate
txn_id_counter = 1
all_txns = []
all_items = []
events_dict = events.to_dicts()
for ev in events_dict:
    venue_id = ev["venue_id"]
    attendance_v = ev["attendance"]
    temp = ev["temp_f"]
    precip_v = ev["precipitation_in"]
    is_we = ev["is_weekend"]
    event_id = ev["event_id"]
    event_date = ev["event_date"]
    # Per-cap transaction rate ~ 0.6-0.9 base; bumped by weather and weekend
    base_rate = 0.65
    weather_mult = 1.0 + 0.005 * max(0, temp - 70) - 0.20 * min(precip_v, 1.0)
    weather_mult = max(0.5, min(weather_mult, 1.25))
    weekend_mult = 1.05 if is_we else 1.0
    txn_rate = base_rate * weather_mult * weekend_mult
    n_txn = int(attendance_v * txn_rate * 0.04)  # ~4% of attendees buy per "transaction window"
    n_txn = max(50, min(n_txn, 3000))

    stands_at_v = venue_stands[venue_id]
    # Assign stands weighted by type (general gets more traffic)
    stand_weights = np.array([
        {"general": 4.0, "specialty": 2.0, "premium": 1.0, "bar": 2.5}[stand_lookup[s][1]]
        for s in stands_at_v
    ])
    stand_weights /= stand_weights.sum()
    chosen_stands = rng.choice(stands_at_v, size=n_txn, p=stand_weights)

    # Transaction timestamps: gate opens ~2hr before, peak in first 1-2 innings/quarter
    # Use a beta-distributed offset 0-4 hours
    minute_offsets = (rng.beta(2.0, 3.5, size=n_txn) * 240).astype(int)
    base_ts = np.datetime64(event_date, "m") + np.timedelta64(17 * 60, "m")  # 5pm baseline
    txn_ts = base_ts + minute_offsets.astype("timedelta64[m]")

    # Items per transaction: 1-5, biased toward 1-2
    items_per_txn = rng.choice([1, 2, 3, 4, 5], size=n_txn, p=[0.40, 0.30, 0.18, 0.08, 0.04])

    # Payment method
    payments = rng.choice(PAYMENT_METHODS, size=n_txn, p=PAYMENT_WEIGHTS)

    # Build line items vectorized (loop only over n_txn because items-per-txn varies)
    txn_totals = np.zeros(n_txn)
    for ti in range(n_txn):
        s = chosen_stands[ti]
        items_at_s = stand_items_map[s]
        n_items = int(items_per_txn[ti])
        # Item probability adjusted by weather:
        # - hot drinks (coffee/hot choc indices 16,17) up when cold
        # - beers (0-9) up when warm
        cats = item_categories[items_at_s]
        prem = item_is_premium[items_at_s]
        w = np.ones(len(items_at_s))
        if temp > 80:
            w[cats == "beer"] *= 1.6
            w[cats == "soft_drink"] *= 1.3
        elif temp < 50:
            w[cats == "beer"] *= 0.7
            # boost hot drinks
            for k, idx in enumerate(items_at_s):
                if MENU[idx][0].startswith("Hot "):
                    w[k] *= 2.5
        if precip_v > 0.2:
            w[cats == "beer"] *= 0.8
        # Stand_type already controls premium probability via menu eligibility
        w /= w.sum()
        picked_local = rng.choice(len(items_at_s), size=n_items, p=w)
        for local_idx in picked_local:
            global_idx = items_at_s[local_idx]
            qty = 1 if rng.random() < 0.92 else 2
            unit_price = menu_price[global_idx]
            line_total = qty * unit_price
            txn_totals[ti] += line_total
            all_items.append((
                f"T{txn_id_counter + ti:07d}",
                f"M{global_idx + 1:03d}",
                qty,
                float(unit_price),
                float(line_total),
            ))

    for ti in range(n_txn):
        all_txns.append((
            f"T{txn_id_counter + ti:07d}",
            chosen_stands[ti],
            event_id,
            str(txn_ts[ti]),
            float(np.round(txn_totals[ti], 2)),
            str(payments[ti]),
            int(items_per_txn[ti]),
        ))
    txn_id_counter += n_txn

print(f"  Generated {len(all_txns):,} transactions, {len(all_items):,} line items")

transactions = pl.DataFrame(
    all_txns,
    schema=["transaction_id", "stand_id", "event_id", "transaction_ts", "total_usd", "payment_method", "item_count"],
    orient="row",
).with_columns(pl.col("transaction_ts").str.to_datetime())

transaction_items = pl.DataFrame(
    all_items,
    schema=["transaction_id", "item_id", "quantity", "unit_price_usd", "line_total_usd"],
    orient="row",
)

# -------------------------------------------------------------------------
# 8. Staff
# -------------------------------------------------------------------------
print("Generating staff...")
N_STAFF = 1200
staff_venue_idx = rng.integers(0, len(VENUES), size=N_STAFF)
staff_role = rng.choice(STAFF_ROLES, size=N_STAFF, p=[0.45, 0.20, 0.15, 0.10, 0.07, 0.03])
hourly_rate_by_role = {"Cashier": 18.0, "Cook": 21.0, "Server": 19.0, "Bartender": 22.0,
                       "Stand Lead": 26.0, "Manager": 34.0}
hourly = np.array([hourly_rate_by_role[r] + rng.normal(0, 1.2) for r in staff_role]).round(2)
hire_offsets = rng.integers(0, 1500, size=N_STAFF)
hire_dates = (np.datetime64("2020-01-01") + hire_offsets.astype("timedelta64[D]"))

staff = pl.DataFrame({
    "staff_id":         [f"P{i+1:05d}" for i in range(N_STAFF)],
    "venue_id":         [f"V{int(i)+1:03d}" for i in staff_venue_idx],
    "role":             staff_role.tolist(),
    "hourly_rate_usd":  hourly.tolist(),
    "hire_date":        hire_dates.astype("datetime64[D]").astype("datetime64[ns]").tolist(),
})

# -------------------------------------------------------------------------
# 9. Labor shifts
# -------------------------------------------------------------------------
print("Generating labor_shifts...")
# Map venue_id -> staff ids
venue_staff = {}
for i, vi in enumerate(staff_venue_idx):
    venue_staff.setdefault(f"V{vi+1:03d}", []).append(f"P{i+1:05d}")

shift_rows = []
shift_id_counter = 1
for ev in events_dict:
    venue_id = ev["venue_id"]
    available = venue_staff.get(venue_id, [])
    if not available:
        continue
    # 40-70 staff scheduled per event depending on attendance %
    pct = ev["attendance"] / [v[3] for v in VENUES][int(venue_id[1:]) - 1]
    n_shifts = int(40 + pct * 30)
    n_shifts = min(n_shifts, len(available))
    chosen_staff = rng.choice(available, size=n_shifts, replace=False)
    # Determine role from staff lookup
    staff_role_lookup = dict(zip(
        [f"P{i+1:05d}" for i in range(N_STAFF)],
        staff_role.tolist()
    ))
    staff_rate_lookup = dict(zip(
        [f"P{i+1:05d}" for i in range(N_STAFF)],
        hourly.tolist()
    ))
    event_date = ev["event_date"]
    base_start = np.datetime64(event_date, "m") + np.timedelta64(15 * 60, "m")  # 3pm
    for sid in chosen_staff:
        start_offset = int(rng.integers(0, 60))
        duration_min = int(rng.integers(300, 480))  # 5-8h
        start_ts = base_start + np.timedelta64(start_offset, "m")
        end_ts = start_ts + np.timedelta64(duration_min, "m")
        hours = round(duration_min / 60, 2)
        rate = staff_rate_lookup[sid]
        shift_rows.append({
            "shift_id": f"SH{shift_id_counter:06d}",
            "event_id": ev["event_id"],
            "staff_id": sid,
            "role":     staff_role_lookup[sid],
            "shift_start_ts": str(start_ts),
            "shift_end_ts":   str(end_ts),
            "hours_worked":   hours,
            "labor_cost_usd": round(hours * rate, 2),
        })
        shift_id_counter += 1
labor_shifts = pl.DataFrame(shift_rows).with_columns(
    pl.col("shift_start_ts").str.to_datetime(),
    pl.col("shift_end_ts").str.to_datetime(),
)

# -------------------------------------------------------------------------
# 10. Inventory movements
# -------------------------------------------------------------------------
print("Generating inventory_movements...")
# For each event, sample ~125 (venue_id, item_id) movements that approximate top-selling SKUs
inv_rows = []
# Group transaction_items + transactions to get event-item sold qtys
print("  Aggregating sales for inventory base...")
event_item_sold = (
    transaction_items
    .join(transactions.select("transaction_id", "event_id", "stand_id"), on="transaction_id")
    .group_by(["event_id", "item_id"])
    .agg(pl.col("quantity").sum().alias("sold_qty"))
)
# Add venue_id
event_item_sold = event_item_sold.join(events.select("event_id", "venue_id"), on="event_id")

# For each event, sample up to 125 items (the top SKUs by sold_qty) for inventory tracking
event_item_sold = event_item_sold.sort(["event_id", "sold_qty"], descending=[False, True])
# Group head 125 per event
sold_rows = event_item_sold.to_dicts()
event_seen = {}
sampled = []
for r in sold_rows:
    c = event_seen.get(r["event_id"], 0)
    if c < 125:
        sampled.append(r)
        event_seen[r["event_id"]] = c + 1

for r in sampled:
    sold = int(r["sold_qty"])
    # Opening qty has padding 15-40%
    opening = int(sold * rng.uniform(1.15, 1.45))
    # Waste: higher for fresh items (burger, hot_dog, pizza); low for beer/water
    item_idx = int(r["item_id"][1:]) - 1
    cat = MENU[item_idx][1]
    waste_rate = {
        "burger": 0.07, "hot_dog": 0.06, "pizza": 0.05, "snack": 0.03,
        "premium": 0.04, "kids": 0.04, "beer": 0.005, "soft_drink": 0.005,
    }[cat]
    waste = int(sold * waste_rate * rng.uniform(0.5, 1.8))
    closing = max(0, opening - sold - waste)
    inv_rows.append({
        "venue_id":    r["venue_id"],
        "event_id":    r["event_id"],
        "item_id":     r["item_id"],
        "opening_qty": opening,
        "sold_qty":    sold,
        "waste_qty":   waste,
        "closing_qty": closing,
    })
inventory_movements = pl.DataFrame(inv_rows)

# -------------------------------------------------------------------------
# Write to UC
# -------------------------------------------------------------------------
print("\nConnecting to Databricks...")
spark = DatabricksSession.builder.serverless().getOrCreate()

print(f"Creating schema {CATALOG}.{SCHEMA}...")
spark.sql(f"CREATE SCHEMA IF NOT EXISTS {CATALOG}.{SCHEMA}")


def write(df: pl.DataFrame, name: str) -> None:
    print(f"  Writing {name} ({len(df):,} rows)...")
    pdf = df.to_pandas()
    sdf = spark.createDataFrame(pdf)
    (sdf.write.format("delta")
        .mode("overwrite")
        .option("overwriteSchema", "true")
        .saveAsTable(f"{CATALOG}.{SCHEMA}.{name}"))


write(venues,              "venues")
write(events,              "events")
write(menu_items,          "menu_items")
write(concession_stands,   "concession_stands")
write(stand_menu,          "stand_menu")
write(transactions,        "transactions")
write(transaction_items,   "transaction_items")
write(staff,               "staff")
write(labor_shifts,        "labor_shifts")
write(inventory_movements, "inventory_movements")

print("\nDone. Tables:")
for r in spark.sql(f"SHOW TABLES IN {CATALOG}.{SCHEMA}").collect():
    print(f"  {r.tableName}")
spark.stop()
