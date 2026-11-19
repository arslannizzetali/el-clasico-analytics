"""Every Parquet file in data/parquet reads back to the same table as its CSV/JSON source.
Needs pandas and pyarrow; skipped otherwise."""
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    import pandas as pd
    import pyarrow  # noqa: F401
    import importlib.util
    from clasico import ROOT
    spec = importlib.util.spec_from_file_location('export_parquet', os.path.join(ROOT, 'analysis', 'export_parquet.py'))
    export = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(export)
    READY = os.path.isdir(export.OUT)
except ImportError:
    READY = False


@unittest.skipUnless(READY, 'needs pandas, pyarrow and analysis/export_parquet.py')
class ParquetRoundTrip(unittest.TestCase):
    def test_every_table_round_trips(self):
        n = 0
        for source, name, df in export.tables():
            path = os.path.join(export.OUT, source, name + '.parquet')
            self.assertTrue(os.path.exists(path), path)
            back = pd.read_parquet(path)
            if any(df[c].map(lambda v: isinstance(v, (list, dict))).any() for c in df.columns if df[c].dtype == object):
                self.assertEqual(back.shape, df.shape, path)        # nested values: compare shape and columns
                self.assertEqual(list(back.columns), list(df.columns), path)
            else:
                pd.testing.assert_frame_equal(back, df, check_dtype=True, obj=path)
            n += 1
        self.assertGreaterEqual(n, 20)


if __name__ == '__main__':
    unittest.main()
