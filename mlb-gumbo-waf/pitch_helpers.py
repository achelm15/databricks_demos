"""Small, testable helpers that the demo notebooks could call.

These are the kinds of pure functions and Spark transforms that usually grow
ad-hoc inside notebook cells — pulling them into a module is the first step
toward unit-testable data code.

WAF angle: *Reliability* and *Operational Excellence*. A function you can
`pytest` from CI is a function whose behavior is pinned. The `CHECK`
constraints in notebook 03 catch bad **data**; unit tests catch bad **code**
before it ever touches data.
"""

from pyspark.sql import DataFrame
from pyspark.sql import functions as F


# ── Pure Python helpers (no Spark required) ─────────────────────────────────

FASTBALL_CODES   = {"FF", "FT", "FA", "SI", "FC"}
BREAKING_CODES   = {"SL", "CU", "KC", "SV", "ST"}
OFFSPEED_CODES   = {"CH", "FS", "EP", "SC"}


def classify_pitch_family(pitch_type_code: str) -> str:
    """Group a raw MLB pitch code into fastball / breaking / offspeed / other.

    Returns 'unknown' for None/empty inputs so the classifier never explodes on
    pickoffs and other non-pitch events that sneak through upstream.
    """
    if not pitch_type_code:
        return "unknown"
    code = pitch_type_code.upper()
    if code in FASTBALL_CODES:   return "fastball"
    if code in BREAKING_CODES:   return "breaking"
    if code in OFFSPEED_CODES:   return "offspeed"
    return "other"


def strike_pct(strikes: int, pitches: int) -> float:
    """strikes / pitches as a percentage, rounded to 2 decimals. 0 if no pitches."""
    if pitches <= 0:
        return 0.0
    return round(100.0 * strikes / pitches, 2)


def is_plausible_pitch_speed(mph) -> bool:
    """Same guardrail as the CHECK constraint in notebook 03 — keep them in sync.

    15-120 mph accepts a real 21 mph eephus and rejects obvious data bugs.
    NULL is considered plausible (we don't have data to judge).
    """
    if mph is None:
        return True
    return 15 <= mph <= 120


def normalize_side(side_code: str) -> str:
    """Canonicalize a batter-side / pitcher-hand code to 'L' or 'R'.

    MLB GUMBO usually emits 'L' or 'R' but occasionally lower-case, leading
    whitespace, or 'S' for switch-hitters that haven't declared. Return 'U'
    for anything we don't recognize so downstream pivots never get a surprise.
    """
    if not side_code:
        return "U"
    s = side_code.strip().upper()
    return s if s in ("L", "R") else "U"


# ── PySpark transforms (need a real Spark session to test) ──────────────────

def add_pitch_family(df: DataFrame, src_col: str = "pitch_type_code",
                     dest_col: str = "pitch_family") -> DataFrame:
    """Add a pitch-family column derived from pitch_type_code.

    Uses a plain CASE rather than `classify_pitch_family` as a UDF — UDFs
    break Photon vectorization, and this logic is trivially expressible in
    Spark SQL. Keep the Python version around for testing: the CASE and the
    Python should agree, and the tests prove it.
    """
    return df.withColumn(
        dest_col,
        F.when(F.upper(F.col(src_col)).isin(*FASTBALL_CODES), F.lit("fastball"))
         .when(F.upper(F.col(src_col)).isin(*BREAKING_CODES), F.lit("breaking"))
         .when(F.upper(F.col(src_col)).isin(*OFFSPEED_CODES), F.lit("offspeed"))
         .when(F.col(src_col).isNull(), F.lit("unknown"))
         .otherwise(F.lit("other"))
    )


def filter_in_zone_pitches(df: DataFrame) -> DataFrame:
    """Keep only pitches whose plate location was inside the batter's strike zone.

    Uses sz_top/sz_bot (vertical bounds per-batter) and the hard-coded
    horizontal half-width of 0.83 feet (half of a 17" plate + ball).
    """
    return df.filter(
        (F.col("plate_z") <= F.col("sz_top"))
        & (F.col("plate_z") >= F.col("sz_bot"))
        & (F.abs(F.col("plate_x")) <= F.lit(0.83))
    )


def pitcher_strike_rate(df: DataFrame, min_pitches: int = 200) -> DataFrame:
    """Aggregate a pitch-grain DataFrame into one row per pitcher with strike %.

    Mirrors the logic in `gold.v_pitcher_leaderboard` so tests of this function
    also pin the dashboard view's semantics.
    """
    return (
        df.groupBy("pitcher_sk", "pitcher_name", "pitcher_hand")
          .agg(
              F.count("*").alias("pitches"),
              F.sum(F.when(F.col("is_strike"), 1).otherwise(0)).alias("strikes"),
              F.avg("start_speed_mph").alias("avg_velocity_mph"),
          )
          .filter(F.col("pitches") >= min_pitches)
          .withColumn("strike_pct",
                      F.round(100.0 * F.col("strikes") / F.col("pitches"), 2))
    )
