# Unit tests for `mlb-gumbo-waf`

These tests pin the behavior of the helpers in `../pitch_helpers.py`. That
module hosts pure-Python + Spark functions that would otherwise have grown
ad-hoc inside notebook cells — pulling them out made them unit-testable, and
every CI run now catches a regression before it reaches a pipeline.

## WAF angle

| WAF pillar | What the test suite buys you |
|------------|-------------------------------|
| **Reliability** | `CHECK` constraints in notebook 03 catch bad *data*; these tests catch bad *code*. Two complementary layers of defence. |
| **Operational Excellence** | Fast (pure-Python tests run in ms) + repeatable (same input → same output) — wire into `pre-commit` or GitHub Actions to block merges that break the classifier. |
| **Data Governance** | `test_add_pitch_family_matches_python` proves the Spark-side `CASE` and the Python classifier *agree*. Drift between the two is a classic source of silent data issues. |

## Running the tests

```bash
cd mlb-gumbo-waf
source .venv/bin/activate
pytest tests/ -v
```

Pure-Python tests run without hitting Databricks. The Spark transform tests
spin up a Databricks Connect session via the shared `spark` fixture in
`conftest.py` and run against serverless compute in your workspace — make
sure your `.env` is set up before running them.

## Extending

- Add a new pure function to `pitch_helpers.py` → add a matching class in
  `test_pure_python.py`.
- Add a new Spark transform → add a fixture row that exercises it and a test
  in `test_spark_transforms.py`.
