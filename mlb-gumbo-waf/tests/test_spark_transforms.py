"""Spark-transform tests — uses the shared `spark` fixture from conftest.

These are slower than the pure-Python tests because they hit Databricks
Connect, but they pin the real shape of our analytics logic.
"""
from pyspark.sql import functions as F

from pitch_helpers import (
    add_pitch_family,
    filter_in_zone_pitches,
    pitcher_strike_rate,
)


def test_add_pitch_family_matches_python(sample_pitch_df):
    """The Spark CASE and the Python classifier should agree on every row —
    if they ever drift, *this test* fires before a pipeline does."""
    from pitch_helpers import classify_pitch_family

    rows = add_pitch_family(sample_pitch_df).collect()
    for r in rows:
        assert r["pitch_family"] == classify_pitch_family(r["pitch_type_code"])


def test_filter_in_zone_drops_out_of_zone(sample_pitch_df):
    """Pitches with plate_x beyond ±0.83 ft or plate_z outside [sz_bot, sz_top]
    must be excluded. p3 in the fixture is out of zone; everything else is in."""
    result = filter_in_zone_pitches(sample_pitch_df).collect()
    ids = {r["pitch_sk"] for r in result}
    assert "p3" not in ids            # out of zone — excluded
    assert "p1" in ids and "p2" in ids  # in zone


def test_pitcher_strike_rate_applies_min_pitches(sample_pitch_df):
    """Strike-rate aggregate respects the min_pitches threshold — with 200 it
    should be empty; with 3 it should return both pitchers."""
    empty = pitcher_strike_rate(sample_pitch_df, min_pitches=200).collect()
    assert len(empty) == 0

    small = pitcher_strike_rate(sample_pitch_df, min_pitches=3).collect()
    names = {r["pitcher_name"] for r in small}
    assert names == {"Paul Skenes", "Emmanuel Clase"}


def test_pitcher_strike_rate_arithmetic(sample_pitch_df):
    """Verify the strike_pct column is actually strikes/pitches*100."""
    result = {r["pitcher_name"]: r for r in
              pitcher_strike_rate(sample_pitch_df, min_pitches=1).collect()}

    # Skenes fixture: 5 pitches, 4 strikes → 80.0%
    assert result["Paul Skenes"]["pitches"] == 5
    assert result["Paul Skenes"]["strikes"] == 4
    assert result["Paul Skenes"]["strike_pct"] == 80.0

    # Clase fixture: 4 pitches (3 SL + 1 None/pickoff), 3 strikes → 75.0%
    assert result["Emmanuel Clase"]["pitches"] == 4
    assert result["Emmanuel Clase"]["strikes"] == 3
    assert result["Emmanuel Clase"]["strike_pct"] == 75.0
