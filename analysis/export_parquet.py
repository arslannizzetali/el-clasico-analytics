"""Write every processed table as Parquet too: data/parquet/<source>/<table>.parquet.

    python3 analysis/export_parquet.py

Sources: data/processed (the reference Clásico pipeline; JSON tables give their `rows`), data/league and data/bi.
CSV/JSON stay the canonical, diffable outputs (CI checks them byte for byte); Parquet is a typed, compressed copy
for tools that read it (DuckDB, Spark, pandas, Power BI). Columns keep the dtypes pandas infers from the CSV, and
tests/test_parquet.py checks every file reads back to the same table.
"""
import json
import os
import sys

import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from clasico import ROOT  # noqa: E402
from clasico.log import get_logger  # noqa: E402

OUT = os.path.join(ROOT, 'data', 'parquet')
SOURCES = {'processed': os.path.join(ROOT, 'data', 'processed'),
           'league': os.path.join(ROOT, 'data', 'league'),
           'bi': os.path.join(ROOT, 'data', 'bi')}
log = get_logger('export_parquet')


def tables():
    """(source, name, DataFrame) for every CSV, and every JSON table without a CSV twin."""
    for source, folder in SOURCES.items():
        names = sorted(os.listdir(folder))
        csvs = {n[:-4] for n in names if n.endswith('.csv')}
        for n in names:
            path = os.path.join(folder, n)
            if n.endswith('.csv'):
                yield source, n[:-4], pd.read_csv(path)
            elif n.endswith('.json') and n[:-5] not in csvs:
                with open(path, encoding='utf-8') as fh:
                    d = json.load(fh)
                rows = d['rows'] if isinstance(d, dict) else d
                if rows and isinstance(rows[0], dict):
                    yield source, n[:-5], pd.json_normalize(rows, max_level=0)


def main():
    n = 0
    for source, name, df in tables():
        os.makedirs(os.path.join(OUT, source), exist_ok=True)
        df.to_parquet(os.path.join(OUT, source, name + '.parquet'), index=False, compression='zstd')
        log.info('wrote parquet', extra={'source': source, 'table': name, 'rows': len(df), 'columns': df.shape[1]})
        n += 1
    log.info('parquet done', extra={'tables': n, 'path': os.path.relpath(OUT, ROOT)})


if __name__ == '__main__':
    main()
