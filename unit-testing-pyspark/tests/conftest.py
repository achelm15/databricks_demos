"""
Shared pytest fixtures for the baseball stats test suite.

conftest.py is a special pytest file — any fixture defined here is
automatically available to ALL test files in this directory without
needing to import it. Think of it as the "setup" that runs before
your tests.
"""

import sys
import os
import pytest

# Add parent directory so we can import baseball_stats
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from databricks.connect import DatabricksSession
from pyspark.sql.types import (
    StructType, StructField, StringType, IntegerType, DoubleType
)


@pytest.fixture(scope="session")
def spark():
    """
    Create a Spark session via Databricks Connect for testing.

    scope="session" means this fixture is created ONCE and shared across
    ALL tests in the entire test run. This is important because starting
    a SparkSession is slow, and we don't want to pay that cost for every
    single test.

    This uses Databricks Connect — your code runs locally but Spark
    operations execute on a remote Databricks cluster or serverless
    compute. Configure your connection via:
      - ~/.databrickscfg profile
      - Environment variables (DATABRICKS_HOST, DATABRICKS_CLUSTER_ID)
      - Or the Databricks SDK's default auth chain
    """
    session = DatabricksSession.builder.serverless(True).getOrCreate()
    yield session
    session.stop()


@pytest.fixture
def batting_schema():
    """Schema for the batting stats DataFrame used across multiple tests."""
    return StructType([
        StructField("player",    StringType(),  True),
        StructField("team",      StringType(),  True),
        StructField("hits",      IntegerType(), True),
        StructField("at_bats",   IntegerType(), True),
        StructField("singles",   IntegerType(), True),
        StructField("doubles",   IntegerType(), True),
        StructField("triples",   IntegerType(), True),
        StructField("home_runs", IntegerType(), True),
    ])


@pytest.fixture
def sample_batting_df(spark, batting_schema):
    """
    A small DataFrame of fictional batting stats for testing.

    Using made-up data is intentional — unit tests should NEVER depend
    on production data. We control exactly what goes in so we can
    predict exactly what comes out.
    """
    data = [
        ("Mike Trout",      "Angels",  180, 550, 100, 30, 5,  45),
        ("Shohei Ohtani",   "Dodgers", 190, 500, 95,  35, 3,  57),
        ("Mookie Betts",    "Dodgers", 170, 520, 90,  40, 4,  36),
        ("Aaron Judge",     "Yankees", 160, 480, 75,  25, 2,  58),
        ("Ronald Acuna Jr", "Braves",  175, 540, 100, 35, 5,  35),
        ("Bench Warmer",    "Mets",    5,   20,  4,   1,  0,  0),
    ]
    return spark.createDataFrame(data, batting_schema)
