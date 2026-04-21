"""Pure-Python unit tests — no Spark, runs in milliseconds.

This is the first place you should add tests: logic you can exercise without
spinning up a SparkSession runs fastest and is easiest to reason about.
"""
import pytest

from pitch_helpers import (
    classify_pitch_family,
    strike_pct,
    is_plausible_pitch_speed,
    normalize_side,
)


class TestClassifyPitchFamily:
    @pytest.mark.parametrize("code,expected", [
        ("FF", "fastball"), ("FT", "fastball"), ("SI", "fastball"), ("FC", "fastball"),
        ("SL", "breaking"), ("CU", "breaking"), ("KC", "breaking"), ("ST", "breaking"),
        ("CH", "offspeed"), ("FS", "offspeed"), ("EP", "offspeed"),
        ("XX", "other"),   ("PO", "other"),
        ("",   "unknown"), (None, "unknown"),
        ("ff", "fastball"),  # case-insensitive
    ])
    def test_classification(self, code, expected):
        assert classify_pitch_family(code) == expected


class TestStrikePct:
    def test_typical(self):
        assert strike_pct(60, 100) == 60.0

    def test_zero_pitches_returns_zero(self):
        # Edge case: division by zero would be a silent bug
        assert strike_pct(0, 0) == 0.0

    def test_rounds_to_two_decimals(self):
        assert strike_pct(1, 3) == 33.33

    def test_perfect(self):
        assert strike_pct(5, 5) == 100.0


class TestIsPlausiblePitchSpeed:
    @pytest.mark.parametrize("mph,expected", [
        (95.0, True),   # normal fastball
        (21.7, True),   # eephus — the CHECK constraint in notebook 03 accepts this
        (None, True),   # NULL is fine, we don't have data to judge
        (14.9, False),  # too slow
        (120.1, False), # no human throws 120+
        (0,    False),
    ])
    def test_ranges(self, mph, expected):
        assert is_plausible_pitch_speed(mph) == expected


class TestNormalizeSide:
    @pytest.mark.parametrize("raw,expected", [
        ("L", "L"), ("R", "R"),
        ("l", "L"), (" r ", "R"),  # whitespace / case tolerant
        ("S", "U"),                # switch-hitters → 'U' so downstream pivots are safe
        ("", "U"), (None, "U"),
    ])
    def test_normalize(self, raw, expected):
        assert normalize_side(raw) == expected
