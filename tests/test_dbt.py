"""The dbt mart (dbt/models/marts/fct_match_team.sql) gives the same numbers as the Python code:

- on the 29 Clásicos, against the reference pipeline's data/processed/match_team.csv
- on every loaded match, against the pandas metrics in data/bi/fact_match_team.csv (all 1,746 team rows locally;
  the Clásicos and finals in CI)

Needs PostgreSQL with `dbt build` run (schema marts); skipped otherwise.
"""
import csv
import os
import sys
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
from clasico import PROCESSED  # noqa: E402

try:
    from clasico import db
    with db.connect() as _c:
        _rows = _c.execute('SELECT match_id, team, passes, pressures, pressures_won_5s, def_actions, opp_passes, '
                           'opp_buildup_passes, ppda, press_success_pct, goals_for, points FROM marts.fct_match_team').fetchall()
    MART = {(r[0], r[1]): r for r in _rows}
    READY = bool(MART)
except Exception:  # psycopg missing, database down, or dbt not run
    READY = False
if os.environ.get('REQUIRE_DB') and not READY:
    raise RuntimeError('REQUIRE_DB is set but marts.fct_match_team is missing (run dbt build)')

COUNTS = ('passes', 'pressures', 'pressures_won_5s', 'def_actions', 'opp_passes', 'opp_buildup_passes')
COL = {c: i for i, c in enumerate(('match_id', 'team') + COUNTS + ('ppda', 'press_success_pct', 'goals_for', 'points'))}


def read(path):
    with open(path, encoding='utf-8') as fh:
        return {(int(r['match_id']), r['team']): r for r in csv.DictReader(fh)}


@unittest.skipUnless(READY, 'needs PostgreSQL and `dbt build`')
class DbtSameAsPython(unittest.TestCase):
    def check(self, ref, keys):
        for k in keys:
            m = MART[k]
            for c in COUNTS:
                self.assertEqual(int(ref[k][c]), m[COL[c]], f'{k} {c}')
            self.assertAlmostEqual(float(ref[k]['ppda']), float(m[COL['ppda']]), delta=0.051, msg=f'{k} ppda')
            if ref[k]['press_success_pct'] not in ('', 'None'):
                self.assertAlmostEqual(float(ref[k]['press_success_pct']), float(m[COL['press_success_pct']]), delta=0.051)

    def test_clasicos_match_reference_pipeline(self):
        ref = read(os.path.join(PROCESSED, 'match_team.csv'))
        self.assertEqual(len(ref), 58)
        self.check(ref, ref)

    def test_every_match_matches_pandas(self):
        ref = read(os.path.join(ROOT, 'data', 'bi', 'fact_match_team.csv'))
        keys = [k for k in ref if k in MART]   # CI loads only the Clásicos and the finals; locally every match
        self.assertGreaterEqual(len(keys), 58 + 14, 'at least the Clásicos and the finals are compared')
        self.check(ref, keys)
        for k in keys:
            self.assertEqual(int(ref[k]['points']), MART[k][COL['points']], k)


if __name__ == '__main__':
    unittest.main()
