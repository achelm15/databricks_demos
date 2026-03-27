"""Sample transformation functions that would live in your internal package."""

from pyspark.sql import DataFrame
from pyspark.sql import functions as F


def add_game_date_parts(df: DataFrame, date_col: str = "game_date") -> DataFrame:
    """Add year, month, day columns from a date column."""
    return (
        df.withColumn("game_year", F.year(date_col))
        .withColumn("game_month", F.month(date_col))
        .withColumn("game_day", F.dayofmonth(date_col))
    )


def calculate_batting_avg(df: DataFrame) -> DataFrame:
    """Add batting average column (hits / at_bats)."""
    return df.withColumn(
        "batting_avg",
        F.when(F.col("at_bats") > 0, F.round(F.col("hits") / F.col("at_bats"), 3)).otherwise(0.0),
    )


def flag_quality_start(df: DataFrame) -> DataFrame:
    """Flag pitching starts as quality starts (6+ IP, 3 or fewer ER)."""
    return df.withColumn(
        "is_quality_start",
        (F.col("innings_pitched") >= 6.0) & (F.col("earned_runs") <= 3),
    )
