"""The whole project as a Dagster asset graph, with dependencies and retries.

    pip install -r requirements-pipeline.txt
    dagster dev -m orchestration.clasico_pipeline                                  # UI on localhost:3000
    dagster job execute -m orchestration.clasico_pipeline -j full_pipeline        # everything, from the shell
    CLASICO_SCOPE=ucl_finals dagster job execute -m orchestration.clasico_pipeline -j full_pipeline

    raw_statsbomb ──► postgres_events ──► quality_checks ──► dbt_models
          │                                     │
          │                                     └──► league_tables ──► league_intervals ──┐
          └──► reference_clasico_outputs ───────────────────────────────────────────────────┼──► bi_and_parquet
                                                                                             └──► site

Each asset runs the project's own script in a subprocess, so the command line (Makefile, CI) and the
orchestrator run the same code. Network and database steps retry with exponential backoff; analysis steps
do not (a failure there is a bug, not a transient error). The load scope (all | league | clasico | ucl_finals)
comes from the run config or CLASICO_SCOPE.
"""
import os
import subprocess
import sys

import dagster as dg

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
NETWORK_RETRY = dg.RetryPolicy(max_retries=3, delay=10, backoff=dg.Backoff.EXPONENTIAL, jitter=dg.Jitter.PLUS_MINUS)
DB_RETRY = dg.RetryPolicy(max_retries=2, delay=5, backoff=dg.Backoff.EXPONENTIAL)


class ScopeConfig(dg.Config):
    scope: str = os.environ.get('CLASICO_SCOPE', 'all')


def run(context, *args, cwd=ROOT):
    """Run one project script with this interpreter; its log lines go to the Dagster log, failure raises."""
    cmd = [sys.executable, *args] if args[0].endswith('.py') else list(args)
    context.log.info('running: ' + ' '.join(cmd[1:] if cmd[0] == sys.executable else cmd))
    r = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, env={**os.environ, 'LOG_FORMAT': 'text'})
    for line in (r.stdout + r.stderr).splitlines()[-40:]:
        context.log.info(line)
    if r.returncode != 0:
        raise dg.Failure(description=f'{" ".join(args)} exited with {r.returncode}')
    return r


@dg.asset(group_name='ingest', retry_policy=NETWORK_RETRY,
          description='StatsBomb event and lineup files in the raw cache (scripts/download.py).')
def raw_statsbomb(context, config: ScopeConfig) -> dg.MaterializeResult:
    run(context, 'scripts/download.py', config.scope)
    return dg.MaterializeResult(metadata={'scope': config.scope})


@dg.asset(group_name='ingest', deps=[raw_statsbomb], retry_policy=DB_RETRY,
          description='Matches, lineups, events, standings and categories in PostgreSQL (idempotent, incremental).')
def postgres_events(context, config: ScopeConfig) -> dg.MaterializeResult:
    run(context, 'scripts/load_db.py', config.scope)
    return dg.MaterializeResult(metadata={'scope': config.scope})


@dg.asset(group_name='ingest', deps=[postgres_events],
          description='Data quality checks (clasico/quality.py); fails the run on any error-level check.')
def quality_checks(context) -> None:
    run(context, 'scripts/check_quality.py')


@dg.asset(group_name='transform', deps=[quality_checks], retry_policy=DB_RETRY,
          description='dbt staging -> intermediate -> marts, with their tests (dbt build).')
def dbt_models(context) -> None:
    dbt = os.path.join(os.path.dirname(sys.executable), 'dbt')
    run(context, dbt, 'build', '--profiles-dir', '.', cwd=os.path.join(ROOT, 'dbt'))


@dg.asset(group_name='transform', deps=[raw_statsbomb],
          description='Reference Clásico pipeline (pipeline.py, standard library) -> data/processed.')
def reference_clasico_outputs(context) -> None:
    run(context, 'pipeline.py')


@dg.asset(group_name='analysis', deps=[quality_checks],
          description='League-wide match-team tables per category (analysis/league.py) -> data/league.')
def league_tables(context) -> None:
    run(context, 'analysis/league.py')


@dg.asset(group_name='analysis', deps=[league_tables],
          description='90% bootstrap intervals and finals comparison (analysis/intervals.py).')
def league_intervals(context) -> None:
    run(context, 'analysis/intervals.py')


@dg.asset(group_name='serve', deps=[league_intervals, reference_clasico_outputs],
          description='Power BI / Tableau CSVs (data/bi) and Parquet copies of every table (data/parquet).')
def bi_and_parquet(context) -> None:
    run(context, 'analysis/export_bi.py')
    run(context, 'analysis/export_parquet.py')


@dg.asset(group_name='serve', deps=[league_intervals, reference_clasico_outputs],
          description='Static dashboard docs/index.html and README charts.')
def site(context) -> None:
    run(context, 'site/build_site.py')
    run(context, 'site/readme_charts.py')


ASSETS = [raw_statsbomb, postgres_events, quality_checks, dbt_models, reference_clasico_outputs,
          league_tables, league_intervals, bi_and_parquet, site]

defs = dg.Definitions(
    assets=ASSETS,
    jobs=[dg.define_asset_job('full_pipeline', selection=dg.AssetSelection.all(),
                              description='Download -> load -> quality -> dbt / reference pipeline -> analysis -> exports and site')],
)
