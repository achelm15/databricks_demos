"""
SVG-based PNG generator for NIL analytics pipeline architecture diagram.
Uses system Arial/Helvetica for clean sans-serif text, then converts to PNG
via macOS sips. No third-party Python dependencies required.
"""

import subprocess
import os
import textwrap

# ---------------------------------------------------------------------------
# Layout constants
# ---------------------------------------------------------------------------

W = 1200
MARGIN = 60
BOX_W = 900
CX = W // 2
LEFT = CX - BOX_W // 2   # 150
RIGHT = CX + BOX_W // 2  # 1050

# Top y of each section box
ROW_H = [
    80,    # 0 - data gen
    300,   # 1 - bronze
    520,   # 2 - silver
    740,   # 3 - gold
    970,   # 4 - catalog
    1150,  # 5 - databricks one
]
BOX_HEIGHT = [180, 180, 180, 190, 150, 200]

ARROW_GAP = 12
FONT = "Arial, Helvetica, sans-serif"

# ---------------------------------------------------------------------------
# Color palette (same as before)
# ---------------------------------------------------------------------------

BG = "#f8f9fb"

DATA_GEN_FILL   = "#ecf6ff"
DATA_GEN_BORDER = "#4285f4"
DATA_GEN_TEXT   = "#1e50a0"

BRONZE_FILL   = "#fff3e0"
BRONZE_BORDER = "#b7692a"
BRONZE_TEXT   = "#783c0a"

SILVER_FILL   = "#f0f0f5"
SILVER_BORDER = "#78829b"  # slightly more saturated for border visibility
SILVER_TEXT   = "#323c50"

GOLD_FILL   = "#fffcdc"
GOLD_BORDER = "#c89b00"
GOLD_TEXT   = "#6e5000"

CATALOG_FILL   = "#f0fff0"
CATALOG_BORDER = "#34a853"
CATALOG_TEXT   = "#146428"

DBX_FILL   = "#ffebee"
DBX_BORDER = "#ff4353"
DBX_TEXT   = "#b41428"

ARROW_COLOR  = "#5a6478"
LABEL_BG     = "white"
LABEL_TEXT   = "#3c465a"

BADGE_BG     = "white"
BADGE_BORDER = "#a0aabe"
BADGE_TEXT   = "#505a6e"

SUB_BORDER   = "#c8c8d2"


# ---------------------------------------------------------------------------
# SVG helpers
# ---------------------------------------------------------------------------

def esc(s):
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;")


def rect(x, y, w, h, fill, stroke, rx=0, stroke_width=2, opacity=1.0):
    op = f' fill-opacity="{opacity}"' if opacity != 1.0 else ""
    return (f'<rect x="{x}" y="{y}" width="{w}" height="{h}" '
            f'fill="{fill}"{op} stroke="{stroke}" stroke-width="{stroke_width}" rx="{rx}"/>')


def text(x, y, content, fill, size, anchor="middle", weight="normal", family=FONT):
    return (f'<text x="{x}" y="{y}" font-family="{esc(family)}" font-size="{size}" '
            f'fill="{fill}" text-anchor="{anchor}" font-weight="{weight}" '
            f'dominant-baseline="auto">{esc(content)}</text>')


def arrow_down(cx, y1, y2, color=ARROW_COLOR, stroke_width=3):
    """Vertical downward arrow centered at cx."""
    ah = 12   # arrowhead height
    aw = 9    # arrowhead half-width
    shaft_end = y2 - ah
    return (
        f'<line x1="{cx}" y1="{y1}" x2="{cx}" y2="{shaft_end}" '
        f'stroke="{color}" stroke-width="{stroke_width}" stroke-linecap="round"/>'
        f'<polygon points="{cx},{y2} {cx-aw},{shaft_end} {cx+aw},{shaft_end}" '
        f'fill="{color}"/>'
    )


def badge(x1, y1, x2, y2, label, bg, border, label_color, font_size=11, rx=6):
    mid_x = (x1 + x2) // 2
    mid_y = (y1 + y2) // 2 + font_size // 3
    return (
        rect(x1, y1, x2 - x1, y2 - y1, bg, border, rx=rx, stroke_width=1)
        + text(mid_x, mid_y, label, label_color, font_size)
    )


# ---------------------------------------------------------------------------
# Section box
# ---------------------------------------------------------------------------

def section_box(row_idx, fill, border,
                title, subtitle_lines,
                notebook_label=None, tag_text=None, tag_color=None):
    x1, y1 = LEFT, ROW_H[row_idx]
    bw, bh = BOX_W, BOX_HEIGHT[row_idx]
    x2, y2 = x1 + bw, y1 + bh

    parts = []

    # Main box
    parts.append(rect(x1, y1, bw, bh, fill, border, rx=16, stroke_width=3))

    # Left accent strip
    parts.append(rect(x1 + 3, y1 + 16, 7, bh - 32, border, "none", rx=3))

    # Notebook badge (top-right)
    if notebook_label:
        bw_badge = max(len(notebook_label) * 7 + 16, 80)
        bx1 = x2 - bw_badge - 16
        by1 = y1 + 12
        parts.append(badge(bx1, by1, bx1 + bw_badge, by1 + 22,
                           notebook_label, BADGE_BG, BADGE_BORDER, BADGE_TEXT,
                           font_size=11))

    # Tag badge (top-left)
    if tag_text:
        tc = tag_color if tag_color else border
        tw_badge = max(len(tag_text) * 7 + 14, 60)
        tx1 = x1 + 20
        ty1 = y1 + 12
        # semi-transparent fill: use SVG rgba via fill-opacity
        parts.append(
            f'<rect x="{tx1}" y="{ty1}" width="{tw_badge}" height="20" '
            f'fill="{tc}" fill-opacity="0.15" stroke="{tc}" stroke-width="1" rx="6"/>'
        )
        parts.append(text(tx1 + tw_badge // 2, ty1 + 14, tag_text, tc, 11))

    # Title (below badge row)
    title_y = y1 + 52
    parts.append(text(CX, title_y, title, border, 18, weight="700"))

    # Subtitle lines
    sub_y = title_y + 24
    for i, line in enumerate(subtitle_lines):
        parts.append(text(CX, sub_y + i * 16, line, LABEL_TEXT, 12))

    return "\n".join(parts)


# ---------------------------------------------------------------------------
# Sub-item row inside a section
# ---------------------------------------------------------------------------

def sub_items(row_idx, items, sub_fill, border):
    x1_outer = LEFT
    y1 = ROW_H[row_idx]
    bh = BOX_HEIGHT[row_idx]

    n = len(items)
    inner_w = BOX_W - 80
    item_w = (inner_w - (n - 1) * 12) // n
    start_x = x1_outer + 40
    item_y1 = y1 + 104
    item_y2 = y1 + bh - 18

    parts = []
    for i, item in enumerate(items):
        ix1 = start_x + i * (item_w + 12)
        ih = item_y2 - item_y1
        lines = item.split("\n")
        parts.append(rect(ix1, item_y1, item_w, ih, sub_fill, border, rx=8, stroke_width=1))
        mid_x = ix1 + item_w // 2
        total_text_h = len(lines) * 16
        start_ty = (item_y1 + item_y2) // 2 - total_text_h // 2 + 12
        for j, ln in enumerate(lines):
            parts.append(text(mid_x, start_ty + j * 16, ln, border, 11))

    return "\n".join(parts)


# ---------------------------------------------------------------------------
# Arrow with inline label
# ---------------------------------------------------------------------------

def section_arrow(row_idx, label=None):
    y1 = ROW_H[row_idx] + BOX_HEIGHT[row_idx] + ARROW_GAP
    y2 = ROW_H[row_idx + 1] - ARROW_GAP

    parts = [arrow_down(CX, y1, y2)]

    if label:
        lw = len(label) * 7 + 20
        lx = CX - lw // 2
        ly_mid = (y1 + y2) // 2
        label_h = 22
        ly = ly_mid - label_h // 2
        parts.append(rect(lx, ly, lw, label_h, LABEL_BG, BADGE_BORDER, rx=5, stroke_width=1))
        parts.append(text(CX, ly + 15, label, LABEL_TEXT, 11))

    return "\n".join(parts)


# ---------------------------------------------------------------------------
# Main SVG builder
# ---------------------------------------------------------------------------

def build_svg():
    total_h = ROW_H[-1] + BOX_HEIGHT[-1] + 80
    parts = []

    # SVG header
    parts.append(
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{total_h}" '
        f'viewBox="0 0 {W} {total_h}">'
    )

    # Background
    parts.append(rect(0, 0, W, total_h, BG, "none"))

    # ---- Title ----
    parts.append(text(CX, 34, "NIL Analytics Pipeline on Databricks",
                      DATA_GEN_BORDER, 22, weight="700"))
    parts.append(text(CX, 58, "End-to-End Architecture: Synthetic Data to Databricks One",
                      LABEL_TEXT, 13))

    # ---- Section 0: Data Generation ----
    parts.append(section_box(0,
        DATA_GEN_FILL, DATA_GEN_BORDER,
        "Synthetic Data Generation",
        ["Faker library generates athletes, sponsors, deals, campaigns as JSON",
         "Output written to UC Volume:  raw_data/"],
        notebook_label="Notebook 01",
        tag_text="Data Gen",
        tag_color=DATA_GEN_BORDER))
    parts.append(sub_items(0,
        ["athletes.json", "sponsors.json", "deals.json", "campaigns.json"],
        "#dceeff", DATA_GEN_BORDER))
    parts.append(section_arrow(0, label="Auto Loader batch ingest"))

    # ---- Section 1: Bronze ----
    parts.append(section_box(1,
        BRONZE_FILL, BRONZE_BORDER,
        "Bronze Layer  \u2014  VARIANT Delta Tables",
        ["Auto Loader reads JSON from UC Volume into schema-on-read VARIANT columns"],
        notebook_label="Notebook 02",
        tag_text="Bronze",
        tag_color=BRONZE_BORDER))
    parts.append(sub_items(1,
        ["athletes_raw", "sponsors_raw", "deals_raw", "campaigns_raw"],
        "#fff8eb", BRONZE_BORDER))
    parts.append(section_arrow(1, label="Typed extraction + surrogate keys"))

    # ---- Section 2: Silver ----
    parts.append(section_box(2,
        SILVER_FILL, SILVER_BORDER,
        "Silver Layer  \u2014  Typed & Deduplicated",
        ["data:field::type casting, MD5 surrogate keys, INSERT OVERWRITE"],
        notebook_label="Notebook 03",
        tag_text="Silver",
        tag_color=SILVER_BORDER))
    parts.append(sub_items(2,
        ["athletes", "sponsors", "deals", "campaigns"],
        "#f5f5fc", SILVER_BORDER))
    parts.append(section_arrow(2, label="Star schema modeling"))

    # ---- Section 3: Gold ----
    parts.append(section_box(3,
        GOLD_FILL, GOLD_BORDER,
        "Gold Layer  \u2014  Star Schema + Analytical Views",
        ["Dimensions, facts, and 3 pre-built analytical views for BI consumers"],
        notebook_label="Notebook 04",
        tag_text="Gold",
        tag_color=GOLD_BORDER))
    parts.append(sub_items(3,
        ["dim_athlete", "dim_sponsor", "dim_date", "fact_deals", "fact_campaign_perf"],
        "#fffce1", GOLD_BORDER))
    parts.append(section_arrow(3, label="COMMENT ON + SET TAGS"))

    # ---- Section 4: Catalog Enrichment ----
    parts.append(section_box(4,
        CATALOG_FILL, CATALOG_BORDER,
        "Unity Catalog Enrichment",
        ["COMMENT ON tables/columns, SET TAGS (domain / tier / PII / owner)",
         "Lineage verification via system.access.column_lineage"],
        notebook_label="Notebook 05",
        tag_text="Governance",
        tag_color=CATALOG_BORDER))
    parts.append(section_arrow(4, label="Lakeview API  |  REST API  |  Discover UI"))

    # ---- Section 5: Databricks One ----
    parts.append(section_box(5,
        DBX_FILL, DBX_BORDER,
        "Databricks One Consumer Surface",
        ["Three notebook-driven assets exposed to business stakeholders"],
        notebook_label="Notebooks 06-08",
        tag_text="Databricks One",
        tag_color=DBX_BORDER))

    # Three consumer sub-boxes
    y1_dbx = ROW_H[5]
    bh_dbx = BOX_HEIGHT[5]
    inner_w = BOX_W - 80
    n = 3
    item_w = (inner_w - (n - 1) * 16) // n
    start_x = LEFT + 40
    item_y1 = y1_dbx + 104
    item_y2 = y1_dbx + bh_dbx - 18

    consumer_items = [
        ("AI/BI Dashboard", "Lakeview API", "Notebook 06"),
        ("Genie Space",     "REST API",     "Notebook 07"),
        ("Discover + Domains", "Unity Catalog UI", "Notebook 08"),
    ]
    sub_fills = ["#fff5f6", "#fff0f3", "#ffebee"]

    for i, (title_c, subtitle_c, nb) in enumerate(consumer_items):
        ix1 = start_x + i * (item_w + 16)
        ih = item_y2 - item_y1
        mid_x = ix1 + item_w // 2
        mid_y = (item_y1 + item_y2) // 2

        parts.append(rect(ix1, item_y1, item_w, ih,
                          sub_fills[i], DBX_BORDER, rx=10, stroke_width=2))
        parts.append(text(mid_x, mid_y - 8,  title_c,   DBX_BORDER, 13, weight="600"))
        parts.append(text(mid_x, mid_y + 8,  subtitle_c, LABEL_TEXT, 11))
        parts.append(text(mid_x, mid_y + 24, nb,         BADGE_TEXT, 10))

    # ---- Footer ----
    footer_y = ROW_H[-1] + BOX_HEIGHT[-1] + 32
    parts.append(text(CX, footer_y,
                      "Built with Databricks  |  Unity Catalog  |  Delta Lake  |  Auto Loader",
                      LABEL_TEXT, 12))

    parts.append("</svg>")
    return "\n".join(parts)


# ---------------------------------------------------------------------------
# Write SVG then convert to PNG via sips
# ---------------------------------------------------------------------------

def main():
    assets_dir = os.path.dirname(os.path.abspath(__file__))
    svg_path = os.path.join(assets_dir, "architecture.svg")
    png_path = os.path.join(assets_dir, "architecture.png")

    svg_content = build_svg()
    with open(svg_path, "w", encoding="utf-8") as f:
        f.write(svg_content)
    print(f"SVG written: {svg_path}")

    result = subprocess.run(
        ["sips", "-s", "format", "png", svg_path, "--out", png_path],
        capture_output=True, text=True
    )
    if result.returncode != 0:
        raise RuntimeError(f"sips failed:\n{result.stderr}")

    size = os.path.getsize(png_path)
    print(f"PNG saved:   {png_path}")
    print(f"File size:   {size:,} bytes")


if __name__ == "__main__":
    main()
