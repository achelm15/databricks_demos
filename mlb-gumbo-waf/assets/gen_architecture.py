"""
SVG-based PNG generator for MLB GUMBO WAF architecture diagram.

Shows the medallion pipeline on the left and the 7 WAF pillars on the right —
each pillar highlights which notebooks touch it so the diagram doubles as a
presentation cheat-sheet.

Run: python gen_architecture.py
Requires macOS `sips` for SVG -> PNG (optional — the SVG is the source of truth).
"""

import os
import subprocess

# ---------------------------------------------------------------------------
# Layout
# ---------------------------------------------------------------------------

W = 1400
MARGIN = 60

# Left column: the medallion pipeline
PIPE_LEFT = 70
PIPE_W = 720
PIPE_CX = PIPE_LEFT + PIPE_W // 2

# Right column: WAF pillars panel
PILLAR_LEFT = PIPE_LEFT + PIPE_W + 60   # 850
PILLAR_W = 480
PILLAR_RIGHT = PILLAR_LEFT + PILLAR_W

# Pipeline rows
PIPE_ROWS = [
    # (top_y, height, short_label)
    (110, 150),   # 0 - ingest (notebook 01)
    (290, 140),   # 1 - bronze (02)
    (460, 140),   # 2 - silver (03)
    (630, 140),   # 3 - gold (04)
    (800, 150),   # 4 - WAF stack (05/06/07)
    (980, 140),   # 5 - ML (08)
    (1150, 160),  # 6 - consumer (09/10/11)
]
ARROW_GAP = 12

FONT = "Arial, Helvetica, sans-serif"

# ---------------------------------------------------------------------------
# Colors
# ---------------------------------------------------------------------------

BG = "#f8f9fb"
LABEL_TEXT = "#3c465a"
BADGE_BG = "white"
BADGE_BORDER = "#a0aabe"
BADGE_TEXT = "#505a6e"

# Pipeline row colors
ROW_COLORS = [
    ("#ecf6ff", "#4285f4", "#1e50a0"),  # 0 ingest   blue
    ("#fff3e0", "#b7692a", "#783c0a"),  # 1 bronze
    ("#f0f0f5", "#78829b", "#323c50"),  # 2 silver
    ("#fffcdc", "#c89b00", "#6e5000"),  # 3 gold
    ("#f0fff0", "#34a853", "#146428"),  # 4 WAF stack   green
    ("#efe9fe", "#6b4ed9", "#361f8a"),  # 5 ML  purple
    ("#ffebee", "#ff4353", "#b41428"),  # 6 consumer red
]

# 7 pillars — each with its own accent color
PILLARS = [
    # (label, accent color, notebooks that emphasize it)
    ("1. Data Governance",             "#34a853", "00, 03, 04, 05, 10"),
    ("2. Interoperability & Usability", "#4285f4", "04, 09, 10"),
    ("3. Operational Excellence",      "#b7692a", "01, 02, 08, 09, 10"),
    ("4. Security, Compliance & Privacy", "#ff4353", "05"),
    ("5. Reliability",                 "#c89b00", "02, 03, 06"),
    ("6. Performance Efficiency",      "#6b4ed9", "02, 03, 04, 07"),
    ("7. Cost Optimization",           "#0b8043", "00, 07"),
]

ARROW_COLOR = "#5a6478"


# ---------------------------------------------------------------------------
# SVG helpers
# ---------------------------------------------------------------------------

def esc(s):
    return (s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;"))


def rect(x, y, w, h, fill, stroke, rx=0, stroke_width=2, opacity=1.0):
    op = f' fill-opacity="{opacity}"' if opacity != 1.0 else ""
    return (f'<rect x="{x}" y="{y}" width="{w}" height="{h}" fill="{fill}"{op} '
            f'stroke="{stroke}" stroke-width="{stroke_width}" rx="{rx}"/>')


def text(x, y, content, fill, size, anchor="middle", weight="normal"):
    return (f'<text x="{x}" y="{y}" font-family="{esc(FONT)}" font-size="{size}" '
            f'fill="{fill}" text-anchor="{anchor}" font-weight="{weight}">{esc(content)}</text>')


def arrow_down(cx, y1, y2, color=ARROW_COLOR, sw=3):
    ah, aw = 12, 9
    shaft_end = y2 - ah
    return (
        f'<line x1="{cx}" y1="{y1}" x2="{cx}" y2="{shaft_end}" stroke="{color}" '
        f'stroke-width="{sw}" stroke-linecap="round"/>'
        f'<polygon points="{cx},{y2} {cx-aw},{shaft_end} {cx+aw},{shaft_end}" fill="{color}"/>'
    )


def badge(x, y, label, bg, border, color, size=11):
    w = max(len(label) * 7 + 16, 70)
    return (rect(x, y, w, 22, bg, border, rx=6, stroke_width=1)
            + text(x + w // 2, y + 15, label, color, size))


# ---------------------------------------------------------------------------
# Pipeline row
# ---------------------------------------------------------------------------

def pipeline_row(idx, title, notebook_label, bullets):
    y, h = PIPE_ROWS[idx]
    fill, border, color = ROW_COLORS[idx]
    x, w = PIPE_LEFT, PIPE_W

    parts = []
    parts.append(rect(x, y, w, h, fill, border, rx=14, stroke_width=3))
    # Left accent strip
    parts.append(rect(x + 3, y + 14, 7, h - 28, border, "none", rx=3))

    # Notebook badge top-right
    parts.append(badge(x + w - 110, y + 14, notebook_label, BADGE_BG, BADGE_BORDER, BADGE_TEXT))

    # Title
    parts.append(text(x + w // 2, y + 46, title, color, 17, weight="700"))

    # Bullets
    for i, b in enumerate(bullets):
        parts.append(text(x + w // 2, y + 74 + i * 18, b, LABEL_TEXT, 12))
    return "\n".join(parts)


def vert_arrow(after_idx, label=None):
    y1 = PIPE_ROWS[after_idx][0] + PIPE_ROWS[after_idx][1] + ARROW_GAP
    y2 = PIPE_ROWS[after_idx + 1][0] - ARROW_GAP
    parts = [arrow_down(PIPE_CX, y1, y2)]
    if label:
        lw = len(label) * 7 + 20
        lx = PIPE_CX - lw // 2
        ly = (y1 + y2) // 2 - 11
        parts.append(rect(lx, ly, lw, 22, BADGE_BG, BADGE_BORDER, rx=5, stroke_width=1))
        parts.append(text(PIPE_CX, ly + 15, label, LABEL_TEXT, 11))
    return "\n".join(parts)


# ---------------------------------------------------------------------------
# WAF pillar panel
# ---------------------------------------------------------------------------

def pillar_panel():
    total_h = PIPE_ROWS[-1][0] + PIPE_ROWS[-1][1] + 60
    header_y = PIPE_ROWS[0][0]

    parts = []
    # Panel background
    parts.append(rect(PILLAR_LEFT, header_y, PILLAR_W, total_h - header_y - 10,
                      "white", "#c8c8d2", rx=16, stroke_width=2))

    # Panel title
    parts.append(text(PILLAR_LEFT + PILLAR_W // 2, header_y + 34,
                      "Well-Architected Framework", "#1e50a0", 18, weight="700"))
    parts.append(text(PILLAR_LEFT + PILLAR_W // 2, header_y + 56,
                      "Seven pillars, mapped to notebooks", LABEL_TEXT, 12))

    # Pillar tiles
    tile_top = header_y + 80
    tile_h = 110
    tile_gap = 14
    inner_w = PILLAR_W - 40

    for i, (label, color, notebooks) in enumerate(PILLARS):
        y = tile_top + i * (tile_h + tile_gap)
        x = PILLAR_LEFT + 20
        # Tile background
        parts.append(rect(x, y, inner_w, tile_h, "#f7fafc", color, rx=10, stroke_width=2))
        # Left accent bar
        parts.append(rect(x + 4, y + 10, 6, tile_h - 20, color, "none", rx=3))
        # Title
        parts.append(text(x + 24, y + 30, label, color, 14, anchor="start", weight="700"))
        # Notebooks label
        parts.append(text(x + 24, y + 56, "Notebooks:", LABEL_TEXT, 11, anchor="start"))
        parts.append(text(x + 102, y + 56, notebooks, BADGE_TEXT, 11, anchor="start", weight="600"))
        # Brief description
        blurb = PILLAR_BLURBS.get(label, "")
        if blurb:
            parts.append(text(x + 24, y + 82, blurb, LABEL_TEXT, 11, anchor="start"))
            if blurb.count("||"):
                # second line
                _, line2 = blurb.split("||", 1)
                parts.append(text(x + 24, y + 98, line2.strip(), LABEL_TEXT, 11, anchor="start"))

    return "\n".join(parts)


PILLAR_BLURBS = {
    "1. Data Governance":                 "Comments, tags, RELY PK/FK, lineage — all in UC.",
    "2. Interoperability & Usability":    "Star schema feeds AI/BI + Genie.",
    "3. Operational Excellence":          "Auto Loader + .env + MLflow aliases. || Dashboard + Genie are code.",
    "4. Security, Compliance & Privacy":  "PII column tag + column mask on attendance.",
    "5. Reliability":                     "CHECK constraints, MD5 SKs, DQ results. || Schema-drift rescue column.",
    "6. Performance Efficiency":          "Liquid clustering + Predictive Optimization.",
    "7. Cost Optimization":               "Tag-based chargeback + removeAfter scanner.",
}


# ---------------------------------------------------------------------------
# Build SVG
# ---------------------------------------------------------------------------

def build_svg():
    total_h = PIPE_ROWS[-1][0] + PIPE_ROWS[-1][1] + 70
    parts = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{total_h}" '
             f'viewBox="0 0 {W} {total_h}">']

    # Background
    parts.append(rect(0, 0, W, total_h, BG, "none"))

    # Title
    parts.append(text(W // 2, 44, "MLB GUMBO — WAF Accelerator", "#1e50a0", 24, weight="700"))
    parts.append(text(W // 2, 72,
                      "End-to-end pitch analytics on Databricks, mapped to the Well-Architected Framework",
                      LABEL_TEXT, 13))

    # --- Pipeline rows ---
    parts.append(pipeline_row(0, "MLB GUMBO API  ->  UC Volume", "Notebook 01", [
        "statsapi.mlb.com schedule + live feeds, partitioned by ingest date",
        "Parameterized season / team / date window via .env",
    ]))
    parts.append(vert_arrow(0, "Auto Loader availableNow"))

    parts.append(pipeline_row(1, "Bronze  -  VARIANT Delta", "Notebook 02", [
        "Single VARIANT column + source-file metadata",
        "Liquid clustered on file_batch_time, _rescued safety net",
    ]))
    parts.append(vert_arrow(1, "Typed extraction + MD5 SK"))

    parts.append(pipeline_row(2, "Silver  -  Typed + Constrained", "Notebook 03", [
        "game_data + pitch_data, RELY PK/FK, CHECK constraints",
        "Clustered on (season, official_date[, game_pk])",
    ]))
    parts.append(vert_arrow(2, "Star schema modeling"))

    parts.append(pipeline_row(3, "Gold  -  Star Schema + Views", "Notebook 04", [
        "dim_team / pitcher / batter / venue / date",
        "fact_games + fact_pitches + 3 pre-agg views",
    ]))
    parts.append(vert_arrow(3, "Governance + DQ + Perf/Cost"))

    parts.append(pipeline_row(4, "WAF layer  -  Govern / Quality / Cost", "05  ·  06  ·  07", [
        "05: tags, comments, PII tag, column mask, lineage",
        "06: DQ expectations persisted; 07: chargeback + PO",
    ]))
    parts.append(vert_arrow(4, "Feature / label build"))

    parts.append(pipeline_row(5, "ML  -  Strike Probability in UC", "Notebook 08", [
        "MLflow run, UC Model Registry, champion/challenger alias",
        "Batch inference back into gold.pitch_strike_probability",
    ]))
    parts.append(vert_arrow(5, "Publish"))

    parts.append(pipeline_row(6, "Consumer surface  -  BI, Genie, WAF recap", "09  ·  10  ·  11", [
        "09 Lakeview dashboard (API)  +  10 Genie space (API)",
        "11 pillar-by-pillar walkthrough for the stage",
    ]))

    # --- WAF pillar panel on the right ---
    parts.append(pillar_panel())

    # Footer
    footer_y = PIPE_ROWS[-1][0] + PIPE_ROWS[-1][1] + 42
    parts.append(text(W // 2, footer_y,
                      "Serverless Databricks Connect  ·  Unity Catalog  ·  Auto Loader  ·  Delta / Iceberg  ·  Lakeview  ·  Genie  ·  Models in UC",
                      LABEL_TEXT, 12))

    parts.append("</svg>")
    return "\n".join(parts)


def main():
    here = os.path.dirname(os.path.abspath(__file__))
    svg_path = os.path.join(here, "architecture.svg")
    png_path = os.path.join(here, "architecture.png")

    with open(svg_path, "w") as f:
        f.write(build_svg())
    print(f"SVG written: {svg_path}")

    # Best-effort PNG render (macOS sips). Non-fatal if it fails.
    try:
        result = subprocess.run(
            ["sips", "-s", "format", "png", svg_path, "--out", png_path],
            capture_output=True, text=True
        )
        if result.returncode == 0:
            print(f"PNG written: {png_path} ({os.path.getsize(png_path):,} bytes)")
        else:
            print(f"sips failed (non-fatal): {result.stderr[:200]}")
    except FileNotFoundError:
        print("sips not available — SVG only.")


if __name__ == "__main__":
    main()
