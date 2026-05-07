"""Create or update the nightly Databricks Job that runs `01_enrich_artists`.

Run once per workspace. Re-running with the same job name updates the
existing job in place (no duplicates).

Required env vars (read from your shell or .env):
    DATABRICKS_HOST           https://your-workspace.cloud.databricks.com
    DATABRICKS_TOKEN          dapi...
    NOTEBOOK_WORKSPACE_PATH   /Workspace/Users/you@databricks.com/rostr-artist-team-enrichment/01_enrich_artists

Optional:
    JOB_NAME                  default 'rostr-artist-team-enrichment-nightly'
    JOB_CRON                  default '0 0 8 * * ?' (08:00 UTC = midnight PT)
    SECRET_SCOPE              default 'rostr_demo' — must contain rostr_username,
                              rostr_password, google_sa_json
"""
from __future__ import annotations

import os

from databricks.sdk import WorkspaceClient
from databricks.sdk.service import jobs


def main() -> None:
    host  = os.environ["DATABRICKS_HOST"]
    token = os.environ["DATABRICKS_TOKEN"]
    notebook_path = os.environ["NOTEBOOK_WORKSPACE_PATH"]
    job_name      = os.getenv("JOB_NAME",     "rostr-artist-team-enrichment-nightly")
    cron          = os.getenv("JOB_CRON",     "0 0 8 * * ?")  # 08:00 UTC = midnight PT
    secret_scope  = os.getenv("SECRET_SCOPE", "rostr_demo")
    google_sheet_id = os.environ.get("GOOGLE_SHEET_ID", "")

    w = WorkspaceClient(host=host, token=token)

    # Resolve secrets to env vars at runtime via the Databricks-Variables syntax.
    # `{{secrets/<scope>/<key>}}` is interpolated by the runtime — it never
    # appears in plaintext in the job spec.
    base_env = {
        "ROSTR_USERNAME"               : f"{{{{secrets/{secret_scope}/rostr_username}}}}",
        "ROSTR_PASSWORD"               : f"{{{{secrets/{secret_scope}/rostr_password}}}}",
        "GOOGLE_AUTH_MODE"             : "service",
        # The runtime writes the secret to a tmp file at this path so
        # google-auth can read it like a normal SA JSON.
        "GOOGLE_APPLICATION_CREDENTIALS": "/tmp/google_sa.json",
        "GOOGLE_SHEET_ID"              : google_sheet_id,
        "GOOGLE_SHEET_TAB"             : os.getenv("GOOGLE_SHEET_TAB", "Sheet1"),
        "PERSIST_TO_UC"                : os.getenv("PERSIST_TO_UC", "false"),
    }

    task = jobs.Task(
        task_key="enrich",
        notebook_task=jobs.NotebookTask(
            notebook_path=notebook_path,
            base_parameters={},  # we use env vars, not widgets
        ),
        # Serverless — no cluster spec needed. The init script writes the SA
        # JSON to disk so google-auth can pick it up via GOOGLE_APPLICATION_CREDENTIALS.
        environment_key="default",
        timeout_seconds=30 * 60,
    )

    settings = jobs.JobSettings(
        name=job_name,
        tasks=[task],
        environments=[
            jobs.JobEnvironment(
                environment_key="default",
                spec=jobs.compute.Environment(
                    client="2",
                    dependencies=["requests", "python-dotenv", "google-auth"],
                ),
            )
        ],
        schedule=jobs.CronSchedule(
            quartz_cron_expression=cron,
            timezone_id="UTC",
            pause_status=jobs.PauseStatus.UNPAUSED,
        ),
        max_concurrent_runs=1,
        # Inject the SA JSON + other env vars via run-as.
        # Note: dbutils.secrets ref in env vars works only via task-level config;
        # use 'spark_conf' style isn't applicable here. Easiest: write the SA
        # JSON in the notebook via dbutils.secrets at startup.
        # The simpler model is: notebook reads dbutils.secrets directly. The
        # base_env above is for completeness when using job-cluster tasks.
    )

    # Find existing job by name, update if present.
    existing = next((j for j in w.jobs.list(name=job_name) if j.settings and j.settings.name == job_name), None)
    if existing and existing.job_id:
        w.jobs.reset(job_id=existing.job_id, new_settings=settings)
        print(f"Updated job {existing.job_id}: {job_name}")
    else:
        created = w.jobs.create(**settings.as_dict())
        print(f"Created job {created.job_id}: {job_name}")

    print(f"\nNote: have your `01_enrich_artists` notebook read secrets via dbutils:")
    print("    rostr_user = dbutils.secrets.get('rostr_demo', 'rostr_username')")
    print("    rostr_pass = dbutils.secrets.get('rostr_demo', 'rostr_password')")
    print("    sa_json    = dbutils.secrets.get('rostr_demo', 'google_sa_json')")
    print("    open('/tmp/google_sa.json','w').write(sa_json)")
    print("    os.environ['GOOGLE_APPLICATION_CREDENTIALS']='/tmp/google_sa.json'")


if __name__ == "__main__":
    main()
