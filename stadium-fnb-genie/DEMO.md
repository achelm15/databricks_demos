# Stadium F&B Genie Demo

A Databricks AI/BI Genie demo built on synthetic sports-venue food & beverage concessions data. Generic naming throughout — no customer reference in any catalog/schema/table/column.

## Audience & Format

- **Audience:** Hospitality/F&B operations leadership, BI/analytics teams
- **Format:** Live Genie UI walkthrough — analyst asks questions in natural language, Genie returns SQL + answers
- **Demo day surface:** Genie room only; data is fixed and curated to produce clean answers

## Use Case

Concessions operator running F&B at multiple sports venues wants to ask business questions of their data without writing SQL:

- Sales performance per venue / per event / per stand / per item
- Attendance and weather impact on concession revenue
- Menu mix and category trends
- Labor cost vs. revenue (margin per event)
- Inventory turn and waste
- Premium vs. standard items, loyalty/payment behavior

## Architecture

```
alexander_booth (catalog)
└── stadium_fnb_demo (schema)
    ├── venues                  -- stadiums/arenas
    ├── events                  -- games, concerts (with weather + attendance)
    ├── concession_stands       -- POS locations per venue
    ├── menu_items              -- SKUs / products
    ├── stand_menu              -- which items each stand sells
    ├── transactions            -- header per receipt
    ├── transaction_items       -- line items
    ├── staff                   -- employees
    ├── labor_shifts            -- staff scheduled per event
    └── inventory_movements     -- opening/closing/waste per event x item
```

**Genie Room:** `Stadium F&B Operations` — scoped to the schema, with table descriptions, column comments, sample questions, instructions, and trusted SQL examples.

## Scale (synthetic)

| Table               | Rows (approx) |
| ------------------- | ------------- |
| venues              | 10            |
| events              | 400           |
| concession_stands   | 120           |
| menu_items          | 60            |
| stand_menu          | 1,800         |
| transactions        | 600,000       |
| transaction_items   | ~1.4M         |
| staff               | 1,200         |
| labor_shifts        | 20,000        |
| inventory_movements | 50,000        |

Time range: 2024-04-01 → 2025-09-30 (one full season + change).

## Brand / Style

Generic. No real team or venue names. Venue names use generic compound nouns ("Lakeside Stadium", "Riverbend Arena"). Sports leagues are abstracted to MLB-style/NFL-style/NBA-style/NHL-style.

## Genie Sample Questions

1. Which venue had the highest total concession revenue last season?
2. What's the average per-cap spend per event by venue?
3. How does rain affect beer sales?
4. Which menu items have the worst waste rate?
5. Top 10 best-selling items in the premium category
6. Labor cost as a percent of revenue per event, ranked
7. Which concession stand has the highest sales per transaction?
8. Compare weekend vs. weekday attendance and revenue
9. Which payment method has the highest average ticket size?
10. Show me revenue trend by month
