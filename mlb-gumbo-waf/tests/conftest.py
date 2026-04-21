"""Shared pytest fixtures for the mlb-gumbo-waf test suite.

conftest.py is special — any fixture defined here is automatically available
to every test file in this directory, no imports needed.
"""
import os
import sys
import pytest

# Make `pitch_helpers` importable from the demo root
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from pyspark.sql.types import (
    StructType, StructField, StringType, IntegerType, DoubleType, BooleanType,
)


@pytest.fixture(scope="session")
def spark():
    """Shared Spark session via Databricks Connect (serverless). Created once per test session."""
    from databricks.connect import DatabricksSession
    from dotenv import load_dotenv
    load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))
    session = DatabricksSession.builder.serverless(True).getOrCreate()
    yield session
    session.stop()


@pytest.fixture
def pitch_schema():
    return StructType([
        StructField("pitch_sk",         StringType(),  False),
        StructField("pitcher_sk",       StringType(),  True),
        StructField("pitcher_name",     StringType(),  True),
        StructField("pitcher_hand",     StringType(),  True),
        StructField("pitch_type_code",  StringType(),  True),
        StructField("start_speed_mph",  DoubleType(),  True),
        StructField("plate_x",          DoubleType(),  True),
        StructField("plate_z",          DoubleType(),  True),
        StructField("sz_top",           DoubleType(),  True),
        StructField("sz_bot",           DoubleType(),  True),
        StructField("is_strike",        BooleanType(), True),
    ])


@pytest.fixture
def sample_pitch_df(spark, pitch_schema):
    """A small deterministic DataFrame of ~10 pitch events covering the corner cases
    each test asserts against. Using made-up data on purpose: unit tests must never
    depend on prod data.
    """
    rows = [
        # Skenes — 5 fastballs, 4 strikes, avg velocity 99 mph
        ("p1",  "sk_skenes", "Paul Skenes", "R", "FF",  99.0,  0.1,  2.7, 3.5, 1.6, True),
        ("p2",  "sk_skenes", "Paul Skenes", "R", "FF", 100.0,  0.0,  2.8, 3.5, 1.6, True),
        ("p3",  "sk_skenes", "Paul Skenes", "R", "FF",  98.0,  0.9,  2.0, 3.5, 1.6, False),  # outside zone
        ("p4",  "sk_skenes", "Paul Skenes", "R", "SL",  88.0, -0.2,  2.2, 3.5, 1.6, True),
        ("p5",  "sk_skenes", "Paul Skenes", "R", "CH",  89.0,  0.3,  2.5, 3.5, 1.6, True),
        # Clase — 3 sliders, all strikes
        ("p6",  "sk_clase",  "Emmanuel Clase", "R", "SL", 89.0, 0.1, 2.3, 3.4, 1.5, True),
        ("p7",  "sk_clase",  "Emmanuel Clase", "R", "SL", 88.5, 0.0, 2.2, 3.4, 1.5, True),
        ("p8",  "sk_clase",  "Emmanuel Clase", "R", "SL", 89.5, 0.2, 2.5, 3.4, 1.5, True),
        # Eephus edge case — legit 21 mph pitch
        ("p9",  "sk_barria", "Yu Barria",      "R", "EP", 21.7, 0.0, 2.5, 3.3, 1.5, True),
        # Unknown pitch type (pickoff that slipped into pitch_data)
        ("p10", "sk_clase",  "Emmanuel Clase", "R", None,  None, None, None, None, None, False),
    ]
    return spark.createDataFrame(rows, pitch_schema)
