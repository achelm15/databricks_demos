"""
Test 1: Pure Python unit tests — NO Spark required.

These tests validate the plain Python functions in baseball_stats.py.
They run instantly because there's no Spark overhead. This is the
simplest kind of unit test and where you should start.

HOW UNIT TESTS WORK:
  - Each function starting with "test_" is a separate test case
  - pytest discovers and runs them automatically
  - "assert" checks if a condition is True — if not, the test FAILS
  - Tests should be independent — the order they run in doesn't matter
"""

from baseball_stats import (
    batting_average,
    slugging_percentage,
    on_base_percentage,
    ops,
    era,
    whip,
    classify_hitter,
)


# ── Batting Average ─────────────────────────────────────────────────────────

class TestBattingAverage:
    """Group related tests into a class for organization."""

    def test_normal_calculation(self):
        # 150 hits in 500 at-bats = .300
        assert batting_average(150, 500) == 0.300

    def test_perfect_average(self):
        # Going 3-for-3 = 1.000
        assert batting_average(3, 3) == 1.0

    def test_zero_at_bats_returns_zero(self):
        # Edge case: no at-bats should return 0, not crash with division by zero
        assert batting_average(0, 0) == 0.0

    def test_hitless(self):
        # 0 hits in 100 at-bats = .000
        assert batting_average(0, 100) == 0.0

    def test_rounding(self):
        # 1 hit in 3 at-bats = 0.333 (not 0.3333333...)
        assert batting_average(1, 3) == 0.333


# ── Slugging Percentage ─────────────────────────────────────────────────────

class TestSluggingPercentage:

    def test_singles_only(self):
        # 100 singles in 400 AB = 100 total bases / 400 = .250
        assert slugging_percentage(100, 0, 0, 0, 400) == 0.25

    def test_all_home_runs(self):
        # 10 HR in 10 AB = 40 total bases / 10 = 4.000
        assert slugging_percentage(0, 0, 0, 10, 10) == 4.0

    def test_mixed_hits(self):
        # 80 singles + 20 doubles + 5 triples + 15 HR in 400 AB
        # Total bases = 80 + 40 + 15 + 60 = 195
        # SLG = 195 / 400 = 0.4875 → rounds to 0.487 (Python banker's rounding)
        result = slugging_percentage(80, 20, 5, 15, 400)
        assert result == 0.487

    def test_zero_at_bats(self):
        assert slugging_percentage(0, 0, 0, 0, 0) == 0.0


# ── On-Base Percentage ──────────────────────────────────────────────────────

class TestOnBasePercentage:

    def test_hits_only(self):
        # 150 H, 0 BB, 0 HBP, 500 AB, 0 SF → 150/500 = .300
        assert on_base_percentage(150, 0, 0, 500, 0) == 0.300

    def test_with_walks(self):
        # 150 H, 50 BB, 5 HBP, 500 AB, 5 SF → 205/560 = .366
        assert on_base_percentage(150, 50, 5, 500, 5) == 0.366

    def test_zero_denominator(self):
        assert on_base_percentage(0, 0, 0, 0, 0) == 0.0


# ── OPS ─────────────────────────────────────────────────────────────────────

class TestOPS:

    def test_ops_calculation(self):
        # OBP .350 + SLG .500 = OPS .850
        assert ops(0.350, 0.500) == 0.850

    def test_ops_elite(self):
        # OBP .400 + SLG .600 = OPS 1.000
        assert ops(0.400, 0.600) == 1.0


# ── Pitching Stats ──────────────────────────────────────────────────────────

class TestERA:

    def test_normal_era(self):
        # 30 ER in 100 IP = (30/100) * 9 = 2.70
        assert era(30, 100.0) == 2.70

    def test_zero_innings(self):
        assert era(5, 0.0) == 0.0

    def test_high_era(self):
        # 50 ER in 40 IP = (50/40) * 9 = 11.25
        assert era(50, 40.0) == 11.25


class TestWHIP:

    def test_normal_whip(self):
        # 30 BB + 90 H in 100 IP = 1.20
        assert whip(30, 90, 100.0) == 1.20

    def test_zero_innings(self):
        assert whip(10, 20, 0.0) == 0.0


# ── Classify Hitter ─────────────────────────────────────────────────────────

class TestClassifyHitter:

    def test_elite(self):
        assert classify_hitter(0.320) == "Elite"

    def test_above_average(self):
        assert classify_hitter(0.280) == "Above Average"

    def test_average(self):
        assert classify_hitter(0.250) == "Average"

    def test_below_average(self):
        assert classify_hitter(0.210) == "Below Average"

    def test_struggling(self):
        assert classify_hitter(0.180) == "Struggling"

    def test_boundary_300(self):
        # Exactly .300 should be Elite
        assert classify_hitter(0.300) == "Elite"
