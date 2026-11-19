"""Run the data quality checks (clasico/quality.py) on the loaded database.

    python3 scripts/check_quality.py      # exit code 1 if any error-level check fails

Run after scripts/load_db.py; CI runs it after loading the Clásicos and the finals.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from clasico import db, quality  # noqa: E402
from clasico.log import get_logger  # noqa: E402

log = get_logger('quality')


def main():
    with db.connect() as conn:
        results = quality.run(conn)
    failed = 0
    for c, n, ok in results:
        level = 'info' if ok else ('error' if c.severity == 'error' else 'warning')
        getattr(log, level)('check', extra={'check': c.name, 'severity': c.severity, 'offending': n, 'limit': c.limit,
                                            'result': 'pass' if ok else 'FAIL'})
        failed += (not ok) and c.severity == 'error'
    log.info('quality done', extra={'checks': len(results), 'errors': failed})
    return 1 if failed else 0


if __name__ == '__main__':
    sys.exit(main())
