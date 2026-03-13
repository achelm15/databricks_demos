"""
Test 2: PySpark transformation tests — requires a SparkSession.

These tests validate functions that operate on Spark DataFrames.
The SparkSession is created ONCE via the fixture in conftest.py and
reused across all tests (that's what scope="session" does).

HOW SPARK TESTS WORK:
  - We create small, controlled DataFrames with known data
  - We run our transformation function on them
  - We check the output DataFrame has the expected values
  - .collect() converts a Spark DataFrame to a Python list of Row
    objects so we can inspect individual values

WHY LOCAL SPARK:
  - SparkSession.builder.master("local[*]") runs Spark on your laptop
  - No cluster, no Databricks workspace, no network calls
  - Fast feedback loop — tests finish in seconds
  - The same PySpark code runs identically on a cluster
"""

import pytest
from baseball_stats import (
    add_batting_average,
    add_slugging_pct,
    filter_qualified_batters,
    top_n_by_stat,
    aggregate_team_stats,
)


class TestAddBattingAverage:
    """Tests for the add_batting_average() transformation."""

    def test_adds_column(self, sample_batting_df):
        """The function should add a 'batting_avg' column."""
        result = add_batting_average(sample_batting_df)
        assert "batting_avg" in result.columns

    def test_correct_calculation(self, sample_batting_df):
        """Verify the math: Mike Trout has 180/550 = .327."""
        result = add_batting_average(sample_batting_df)
        trout = result.filter(result.player == "Mike Trout").collect()[0]
        assert trout.batting_avg == 0.327

    def test_preserves_existing_columns(self, sample_batting_df):
        """The function should NOT drop any existing columns."""
        original_cols = set(sample_batting_df.columns)
        result = add_batting_average(sample_batting_df)
        assert original_cols.issubset(set(result.columns))

    def test_row_count_unchanged(self, sample_batting_df):
        """Adding a column should not change the number of rows."""
        result = add_batting_average(sample_batting_df)
        assert result.count() == sample_batting_df.count()


class TestAddSluggingPct:
    """Tests for the add_slugging_pct() transformation."""

    def test_adds_column(self, sample_batting_df):
        result = add_slugging_pct(sample_batting_df)
        assert "slugging_pct" in result.columns

    def test_ohtani_slugging(self, sample_batting_df):
        """
        Ohtani: 95 singles + 35 doubles + 3 triples + 57 HR in 500 AB
        Total bases = 95 + 70 + 9 + 228 = 402
        SLG = 402 / 500 = 0.804
        """
        result = add_slugging_pct(sample_batting_df)
        ohtani = result.filter(result.player == "Shohei Ohtani").collect()[0]
        assert ohtani.slugging_pct == 0.804

    def test_low_at_bats_player(self, sample_batting_df):
        """
        Bench Warmer: 4 singles + 1 double + 0 triples + 0 HR in 20 AB
        Total bases = 4 + 2 + 0 + 0 = 6
        SLG = 6 / 20 = 0.300
        """
        result = add_slugging_pct(sample_batting_df)
        bench = result.filter(result.player == "Bench Warmer").collect()[0]
        assert bench.slugging_pct == 0.3


class TestFilterQualifiedBatters:
    """Tests for the filter_qualified_batters() transformation."""

    def test_default_threshold(self, sample_batting_df):
        """Default min_at_bats=50 should exclude Bench Warmer (20 AB)."""
        result = filter_qualified_batters(sample_batting_df)
        players = [row.player for row in result.collect()]
        assert "Bench Warmer" not in players
        assert len(players) == 5

    def test_custom_threshold(self, sample_batting_df):
        """Setting min_at_bats=500 should keep only players with 500+ AB."""
        result = filter_qualified_batters(sample_batting_df, min_at_bats=500)
        players = [row.player for row in result.collect()]
        # Trout 550, Ohtani 500, Betts 520, Acuna 540 qualify
        # Judge 480 and Bench Warmer 20 do not
        assert "Aaron Judge" not in players
        assert "Bench Warmer" not in players
        assert len(players) == 4

    def test_threshold_zero_returns_all(self, sample_batting_df):
        """min_at_bats=0 should return everyone."""
        result = filter_qualified_batters(sample_batting_df, min_at_bats=0)
        assert result.count() == 6


class TestTopNByStat:
    """Tests for the top_n_by_stat() transformation."""

    def test_top_3_home_runs(self, sample_batting_df):
        """Top 3 HR leaders should be Judge (58), Ohtani (57), Trout (45)."""
        result = top_n_by_stat(sample_batting_df, "home_runs", n=3)
        rows = result.collect()
        assert len(rows) == 3
        assert rows[0].player == "Aaron Judge"
        assert rows[1].player == "Shohei Ohtani"
        assert rows[2].player == "Mike Trout"

    def test_top_1(self, sample_batting_df):
        """Top 1 by hits should be Ohtani (190)."""
        result = top_n_by_stat(sample_batting_df, "hits", n=1)
        rows = result.collect()
        assert len(rows) == 1
        assert rows[0].player == "Shohei Ohtani"


class TestAggregateTeamStats:
    """Tests for the aggregate_team_stats() transformation."""

    def test_team_count(self, sample_batting_df):
        """We should get one row per team (Dodgers have 2 players)."""
        df = add_batting_average(sample_batting_df)
        result = aggregate_team_stats(df)
        assert result.count() == 5  # Angels, Dodgers, Yankees, Braves, Mets

    def test_dodgers_totals(self, sample_batting_df):
        """Dodgers = Ohtani + Betts: 190+170=360 hits, 500+520=1020 AB."""
        df = add_batting_average(sample_batting_df)
        result = aggregate_team_stats(df)
        dodgers = result.filter(result.team == "Dodgers").collect()[0]
        assert dodgers.total_hits == 360
        assert dodgers.total_at_bats == 1020
        assert dodgers.total_home_runs == 93  # 57 + 36
