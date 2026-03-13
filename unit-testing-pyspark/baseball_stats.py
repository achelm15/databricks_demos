"""
Baseball stat functions — the code we want to test.

These are pure Python functions and PySpark transformation functions
that compute common baseball performance metrics.
"""

from pyspark.sql import DataFrame
from pyspark.sql import functions as F


# ── Pure Python functions (no Spark needed) ─────────────────────────────────

def batting_average(hits: int, at_bats: int) -> float:
    """Calculate batting average: hits / at-bats."""
    if at_bats == 0:
        return 0.0
    return round(hits / at_bats, 3)


def slugging_percentage(singles: int, doubles: int, triples: int,
                        home_runs: int, at_bats: int) -> float:
    """Calculate slugging percentage: total bases / at-bats."""
    if at_bats == 0:
        return 0.0
    total_bases = singles + (2 * doubles) + (3 * triples) + (4 * home_runs)
    return round(total_bases / at_bats, 3)


def on_base_percentage(hits: int, walks: int, hbp: int,
                       at_bats: int, sac_flies: int) -> float:
    """Calculate OBP: (H + BB + HBP) / (AB + BB + HBP + SF)."""
    denom = at_bats + walks + hbp + sac_flies
    if denom == 0:
        return 0.0
    return round((hits + walks + hbp) / denom, 3)


def ops(obp: float, slg: float) -> float:
    """OPS = On-Base + Slugging."""
    return round(obp + slg, 3)


def era(earned_runs: int, innings_pitched: float) -> float:
    """Earned Run Average: (ER / IP) * 9."""
    if innings_pitched == 0.0:
        return 0.0
    return round((earned_runs / innings_pitched) * 9, 2)


def whip(walks: int, hits: int, innings_pitched: float) -> float:
    """Walks + Hits per Inning Pitched."""
    if innings_pitched == 0.0:
        return 0.0
    return round((walks + hits) / innings_pitched, 2)


def classify_hitter(avg: float) -> str:
    """Classify a hitter's batting average into a tier."""
    if avg >= 0.300:
        return "Elite"
    elif avg >= 0.270:
        return "Above Average"
    elif avg >= 0.240:
        return "Average"
    elif avg >= 0.200:
        return "Below Average"
    else:
        return "Struggling"


# ── PySpark transformation functions ────────────────────────────────────────

def add_batting_average(df: DataFrame) -> DataFrame:
    """Add a batting_avg column to a DataFrame with hits and at_bats columns."""
    return df.withColumn(
        "batting_avg",
        F.when(F.col("at_bats") == 0, 0.0)
         .otherwise(F.round(F.col("hits") / F.col("at_bats"), 3))
    )


def add_slugging_pct(df: DataFrame) -> DataFrame:
    """Add a slugging_pct column from singles, doubles, triples, home_runs, at_bats."""
    total_bases = (
        F.col("singles")
        + 2 * F.col("doubles")
        + 3 * F.col("triples")
        + 4 * F.col("home_runs")
    )
    return df.withColumn(
        "slugging_pct",
        F.when(F.col("at_bats") == 0, 0.0)
         .otherwise(F.round(total_bases / F.col("at_bats"), 3))
    )


def filter_qualified_batters(df: DataFrame, min_at_bats: int = 50) -> DataFrame:
    """Filter to batters with enough at-bats to qualify for stat leaders."""
    return df.filter(F.col("at_bats") >= min_at_bats)


def top_n_by_stat(df: DataFrame, stat_col: str, n: int = 5) -> DataFrame:
    """Return the top N rows by a given stat column, descending."""
    return df.orderBy(F.col(stat_col).desc()).limit(n)


def aggregate_team_stats(df: DataFrame) -> DataFrame:
    """Aggregate batting stats by team."""
    return df.groupBy("team").agg(
        F.sum("hits").alias("total_hits"),
        F.sum("at_bats").alias("total_at_bats"),
        F.sum("home_runs").alias("total_home_runs"),
        F.avg("batting_avg").alias("avg_batting_avg"),
    )
