"""The Dagster pipeline (orchestration/clasico_pipeline) has the intended graph, retries and job.
Checks the definitions only (no run); needs requirements-pipeline.txt, skipped otherwise.
A full run: `dagster job execute -m orchestration.clasico_pipeline -j full_pipeline`."""
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    import dagster as dg
    from orchestration.clasico_pipeline import defs
    READY = True
except ImportError:
    READY = False

UPSTREAM = {
    'raw_statsbomb': set(),
    'postgres_events': {'raw_statsbomb'},
    'quality_checks': {'postgres_events'},
    'dbt_models': {'quality_checks'},
    'reference_clasico_outputs': {'raw_statsbomb'},
    'league_tables': {'quality_checks'},
    'league_intervals': {'league_tables'},
    'bi_and_parquet': {'league_intervals', 'reference_clasico_outputs'},
    'site': {'league_intervals', 'reference_clasico_outputs'},
}


@unittest.skipUnless(READY, 'needs requirements-pipeline.txt')
class Pipeline(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.graph = defs.resolve_asset_graph()
        cls.assets = {k.to_user_string(): k for k in cls.graph.get_all_asset_keys()}

    def test_graph_is_download_load_build_analysis(self):
        self.assertEqual(set(self.assets), set(UPSTREAM))
        for name, ups in UPSTREAM.items():
            got = {p.to_user_string() for p in self.graph.get(self.assets[name]).parent_keys}
            self.assertEqual(got, ups, name)

    def test_network_and_database_steps_retry(self):
        policies = {a.key.to_user_string(): a.op.retry_policy for a in defs.assets}
        for name in ('raw_statsbomb', 'postgres_events', 'dbt_models'):
            self.assertIsNotNone(policies[name], name)
            self.assertGreaterEqual(policies[name].max_retries, 2, name)
        self.assertEqual(policies['raw_statsbomb'].backoff, dg.Backoff.EXPONENTIAL)
        for name in ('league_tables', 'league_intervals', 'bi_and_parquet', 'site'):
            self.assertIsNone(policies[name], f'{name} should fail fast, not retry')

    def test_full_job_covers_every_asset(self):
        job = defs.resolve_job_def('full_pipeline')
        self.assertEqual({n.name for n in job.graph.node_defs}, set(UPSTREAM))


if __name__ == '__main__':
    unittest.main()
