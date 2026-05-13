"""
Add table descriptions and column comments to stadium_fnb_demo tables.

Run:
    DATABRICKS_CONFIG_PROFILE=DEFAULT python add_comments.py
"""

from databricks.connect import DatabricksSession

CATALOG = "alexander_booth"
SCHEMA = "stadium_fnb_demo"

spark = DatabricksSession.builder.serverless().getOrCreate()

def fq(table: str) -> str:
    return f"{CATALOG}.{SCHEMA}.{table}"

# Table descriptions (these surface in Genie as table summaries)
TABLE_COMMENTS = {
    "venues": "Sports venues operated by the concessions business. One row per stadium or arena. Includes capacity, city, league type, and climate zone.",
    "events": "Single events held at a venue (games, concerts, special events). Includes attendance, weather, sold-out status, and weekend flag. Use this as the primary 'when something happened' table.",
    "menu_items": "Food and beverage SKUs sold at concession stands. Includes retail price, unit cost, category, and a premium flag. Margin = price_usd - unit_cost_usd.",
    "concession_stands": "Physical point-of-sale concession stands inside each venue. A stand has a type (general, premium, specialty, bar) and a vendor partner.",
    "stand_menu": "Which menu items each concession stand offers. Many-to-many bridge between concession_stands and menu_items.",
    "transactions": "Receipt-level concession sales. One row per customer transaction. Join to events for date/weather/attendance context and to concession_stands for venue context.",
    "transaction_items": "Line items inside each transaction. Join to transactions for event context and to menu_items for category and margin.",
    "staff": "Hourly concessions employees assigned to a home venue. Role determines hourly rate.",
    "labor_shifts": "Staff scheduled for a specific event. Use this to compute labor cost per event and labor cost as a percent of concession revenue.",
    "inventory_movements": "Per-event inventory tracking for the top-selling items at each venue. Records opening qty, sold qty, waste qty, and closing qty so you can compute waste rate and inventory turn.",
}

# Column comments per table
COLUMN_COMMENTS = {
    "venues": {
        "venue_id": "Primary key for the venue (e.g. V001).",
        "venue_name": "Display name of the stadium or arena.",
        "city": "U.S. city where the venue is located.",
        "league_type": "League style: MLB-style, NFL-style, NBA-style, NHL-style, or multi-use. Does not refer to real leagues.",
        "capacity": "Maximum seating capacity.",
        "climate_zone": "Coarse climate bucket: cold, temperate, or hot. Drives weather patterns.",
        "opened_year": "Year the venue opened.",
    },
    "events": {
        "event_id": "Primary key for an event (e.g. E00001).",
        "venue_id": "Foreign key to venues.",
        "event_date": "Calendar date the event was held.",
        "event_type": "Type of event: Regular Season Game, Playoff Game, Concert, or Special Event.",
        "home_team": "Always 'Home Club' in this dataset (single-tenant venues).",
        "opponent": "Visiting team or performer label.",
        "attendance": "Number of attendees that day.",
        "sold_out_flag": "1 if the event sold out (attendance pct >= 97%), else 0.",
        "temp_f": "Game-time temperature in degrees Fahrenheit.",
        "precipitation_in": "Rainfall during the event in inches. 0 means dry.",
        "weather_condition": "Categorical weather label: Hot, Warm, Mild, Cold, Light Rain, Rainy.",
        "is_weekend": "1 if the event was on a Saturday or Sunday, else 0.",
    },
    "menu_items": {
        "item_id": "Primary key for a menu item (e.g. M001).",
        "item_name": "Display name of the menu item.",
        "category": "Item category: beer, soft_drink, hot_dog, burger, pizza, snack, premium, kids.",
        "price_usd": "Retail price in U.S. dollars.",
        "unit_cost_usd": "Cost of goods per unit in U.S. dollars. Margin per unit = price_usd - unit_cost_usd.",
        "is_premium": "1 if this is a premium item (higher price, found mostly at premium stands and bars), else 0.",
    },
    "concession_stands": {
        "stand_id": "Primary key for a concession stand (e.g. S01-03).",
        "venue_id": "Foreign key to venues.",
        "stand_name": "Display name of the stand.",
        "concourse_level": "Which concourse the stand is on: Field Level, 100 Level, 200 Level, 300 Level, Club Level, Suite Level.",
        "stand_type": "Stand type: general, premium, specialty, or bar. Drives the menu it offers and traffic weight.",
        "vendor_partner": "Third-party vendor operating the stand.",
    },
    "stand_menu": {
        "stand_id": "Foreign key to concession_stands.",
        "item_id": "Foreign key to menu_items.",
        "available_flag": "1 if the item is currently available at the stand. Currently always 1.",
    },
    "transactions": {
        "transaction_id": "Primary key for the receipt (e.g. T0000123).",
        "stand_id": "Concession stand where the transaction occurred.",
        "event_id": "Foreign key to events. Use this to join attendance, weather, weekend flag.",
        "transaction_ts": "Timestamp of the receipt.",
        "total_usd": "Total receipt value in U.S. dollars.",
        "payment_method": "Mobile, Credit Card, Cash, or Loyalty App.",
        "item_count": "Number of distinct line items on the receipt.",
    },
    "transaction_items": {
        "transaction_id": "Foreign key to transactions.",
        "item_id": "Foreign key to menu_items.",
        "quantity": "Units sold of this item on this receipt.",
        "unit_price_usd": "Price charged per unit on this receipt (matches menu_items.price_usd in this dataset).",
        "line_total_usd": "quantity * unit_price_usd.",
    },
    "staff": {
        "staff_id": "Primary key for an employee (e.g. P00123).",
        "venue_id": "Home venue the employee is assigned to.",
        "role": "Job role: Cashier, Cook, Server, Bartender, Stand Lead, or Manager.",
        "hourly_rate_usd": "Hourly pay rate in U.S. dollars.",
        "hire_date": "Date the employee was hired.",
    },
    "labor_shifts": {
        "shift_id": "Primary key for the shift.",
        "event_id": "Foreign key to events.",
        "staff_id": "Foreign key to staff.",
        "role": "Role worked during this shift (matches staff.role).",
        "shift_start_ts": "Shift clock-in timestamp.",
        "shift_end_ts": "Shift clock-out timestamp.",
        "hours_worked": "Total hours worked on the shift.",
        "labor_cost_usd": "hours_worked * hourly_rate_usd. The labor cost we paid for this shift.",
    },
    "inventory_movements": {
        "venue_id": "Foreign key to venues.",
        "event_id": "Foreign key to events.",
        "item_id": "Foreign key to menu_items.",
        "opening_qty": "Inventory units on hand at the start of the event.",
        "sold_qty": "Units sold during the event.",
        "waste_qty": "Units thrown out (spoilage, prep waste).",
        "closing_qty": "Units remaining at end of event. waste_rate = waste_qty / (sold_qty + waste_qty).",
    },
}


def quote(s: str) -> str:
    return s.replace("'", "''")


for table, comment in TABLE_COMMENTS.items():
    print(f"COMMENT ON TABLE {table}...")
    spark.sql(f"COMMENT ON TABLE {fq(table)} IS '{quote(comment)}'")

for table, cols in COLUMN_COMMENTS.items():
    for col, c in cols.items():
        spark.sql(
            f"ALTER TABLE {fq(table)} ALTER COLUMN {col} COMMENT '{quote(c)}'"
        )
    print(f"  {table}: {len(cols)} columns commented")

# Add primary key + foreign key constraints (informational only, no enforcement)
print("\nAdding informational PK/FK constraints...")
PK_FK = [
    # (alter statement,)
    f"ALTER TABLE {fq('venues')}            ALTER COLUMN venue_id      SET NOT NULL",
    f"ALTER TABLE {fq('events')}            ALTER COLUMN event_id      SET NOT NULL",
    f"ALTER TABLE {fq('menu_items')}        ALTER COLUMN item_id       SET NOT NULL",
    f"ALTER TABLE {fq('concession_stands')} ALTER COLUMN stand_id      SET NOT NULL",
    f"ALTER TABLE {fq('transactions')}      ALTER COLUMN transaction_id SET NOT NULL",
    f"ALTER TABLE {fq('staff')}             ALTER COLUMN staff_id      SET NOT NULL",
    f"ALTER TABLE {fq('labor_shifts')}      ALTER COLUMN shift_id      SET NOT NULL",

    f"ALTER TABLE {fq('venues')}            ADD CONSTRAINT pk_venues            PRIMARY KEY (venue_id) RELY",
    f"ALTER TABLE {fq('events')}            ADD CONSTRAINT pk_events            PRIMARY KEY (event_id) RELY",
    f"ALTER TABLE {fq('menu_items')}        ADD CONSTRAINT pk_menu_items        PRIMARY KEY (item_id) RELY",
    f"ALTER TABLE {fq('concession_stands')} ADD CONSTRAINT pk_concession_stands PRIMARY KEY (stand_id) RELY",
    f"ALTER TABLE {fq('transactions')}      ADD CONSTRAINT pk_transactions      PRIMARY KEY (transaction_id) RELY",
    f"ALTER TABLE {fq('staff')}             ADD CONSTRAINT pk_staff             PRIMARY KEY (staff_id) RELY",
    f"ALTER TABLE {fq('labor_shifts')}      ADD CONSTRAINT pk_labor_shifts      PRIMARY KEY (shift_id) RELY",

    f"ALTER TABLE {fq('events')}            ADD CONSTRAINT fk_events_venue       FOREIGN KEY (venue_id) REFERENCES {fq('venues')}(venue_id) NOT ENFORCED RELY",
    f"ALTER TABLE {fq('concession_stands')} ADD CONSTRAINT fk_stands_venue       FOREIGN KEY (venue_id) REFERENCES {fq('venues')}(venue_id) NOT ENFORCED RELY",
    f"ALTER TABLE {fq('stand_menu')}        ADD CONSTRAINT fk_sm_stand           FOREIGN KEY (stand_id) REFERENCES {fq('concession_stands')}(stand_id) NOT ENFORCED RELY",
    f"ALTER TABLE {fq('stand_menu')}        ADD CONSTRAINT fk_sm_item            FOREIGN KEY (item_id) REFERENCES {fq('menu_items')}(item_id) NOT ENFORCED RELY",
    f"ALTER TABLE {fq('transactions')}      ADD CONSTRAINT fk_txn_stand          FOREIGN KEY (stand_id) REFERENCES {fq('concession_stands')}(stand_id) NOT ENFORCED RELY",
    f"ALTER TABLE {fq('transactions')}      ADD CONSTRAINT fk_txn_event          FOREIGN KEY (event_id) REFERENCES {fq('events')}(event_id) NOT ENFORCED RELY",
    f"ALTER TABLE {fq('transaction_items')} ADD CONSTRAINT fk_ti_txn             FOREIGN KEY (transaction_id) REFERENCES {fq('transactions')}(transaction_id) NOT ENFORCED RELY",
    f"ALTER TABLE {fq('transaction_items')} ADD CONSTRAINT fk_ti_item            FOREIGN KEY (item_id) REFERENCES {fq('menu_items')}(item_id) NOT ENFORCED RELY",
    f"ALTER TABLE {fq('staff')}             ADD CONSTRAINT fk_staff_venue        FOREIGN KEY (venue_id) REFERENCES {fq('venues')}(venue_id) NOT ENFORCED RELY",
    f"ALTER TABLE {fq('labor_shifts')}      ADD CONSTRAINT fk_shift_event        FOREIGN KEY (event_id) REFERENCES {fq('events')}(event_id) NOT ENFORCED RELY",
    f"ALTER TABLE {fq('labor_shifts')}      ADD CONSTRAINT fk_shift_staff        FOREIGN KEY (staff_id) REFERENCES {fq('staff')}(staff_id) NOT ENFORCED RELY",
    f"ALTER TABLE {fq('inventory_movements')} ADD CONSTRAINT fk_inv_venue        FOREIGN KEY (venue_id) REFERENCES {fq('venues')}(venue_id) NOT ENFORCED RELY",
    f"ALTER TABLE {fq('inventory_movements')} ADD CONSTRAINT fk_inv_event        FOREIGN KEY (event_id) REFERENCES {fq('events')}(event_id) NOT ENFORCED RELY",
    f"ALTER TABLE {fq('inventory_movements')} ADD CONSTRAINT fk_inv_item         FOREIGN KEY (item_id) REFERENCES {fq('menu_items')}(item_id) NOT ENFORCED RELY",
]
for stmt in PK_FK:
    try:
        spark.sql(stmt)
    except Exception as e:
        msg = str(e).splitlines()[0]
        print(f"  SKIP: {msg[:120]}")

print("\nDone.")
spark.stop()
