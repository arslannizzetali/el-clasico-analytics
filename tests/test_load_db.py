"""scripts/load_db.py is idempotent and incremental.

- the same command twice: the second run loads nothing and the data is identical (fingerprint of every event)
- incremental: after one match is removed, a rerun loads exactly that match and restores the same data
- --reload twice: matches are replaced, the data is identical

Works on the Champions League finals (7 matches, quick). Needs requirements.txt and PostgreSQL; skipped otherwise.
"""
import importlib.util
import os
import sys
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

try:
    from clasico import db
    with db.connect() as _c:
        _c.execute('SELECT 1')
    READY = True
except Exception:  # psycopg missing or database down
    READY = False
if os.environ.get('REQUIRE_DB') and not READY:
    raise RuntimeError('REQUIRE_DB is set but PostgreSQL is not reachable')

FINGERPRINT = """
SELECT count(DISTINCT m.match_id), count(*),
       md5(string_agg(concat_ws('|', e.event_id, e.match_id, e.idx, e.type, e.team_id, e.player_id, e.ts, e.x, e.y,
                                e.outcome, e.subtype, e.xg, md5(e.raw::text)), ',' ORDER BY e.match_id, e.idx))
FROM matches m JOIN events e USING (match_id) WHERE m.competition_id = 16"""
OTHER = """SELECT (SELECT count(*) FROM lineups l JOIN matches m USING (match_id) WHERE m.competition_id = 16),
                  (SELECT count(*) FROM match_categories WHERE category = 'ucl_finals'),
                  (SELECT md5(string_agg(concat_ws('|', match_id, home_manager, away_manager, home_score, away_score), ','
                               ORDER BY match_id)) FROM matches WHERE competition_id = 16)"""


def loader():
    spec = importlib.util.spec_from_file_location('load_db', os.path.join(ROOT, 'scripts', 'load_db.py'))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod.load


@unittest.skipUnless(READY, 'needs requirements.txt and PostgreSQL')
class Idempotent(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.load = staticmethod(loader())
        cls.load('ucl_finals')   # make sure the finals are there

    def state(self):
        with db.connect() as c:
            return c.execute(FINGERPRINT).fetchone() + c.execute(OTHER).fetchone()

    def test_same_command_twice(self):
        before = self.state()
        r = self.load('ucl_finals')
        self.assertEqual(r['loaded'], 0)
        self.assertEqual(self.state(), before)
        self.assertEqual(before[0], 7)

    def test_incremental_loads_only_the_missing_match(self):
        before = self.state()
        with db.connect() as c:
            mid = c.execute('SELECT min(match_id) FROM matches WHERE competition_id = 16').fetchone()[0]
            c.execute('DELETE FROM matches WHERE match_id = %s', (mid,))
        self.assertEqual(self.state()[0], 6)
        r = self.load('ucl_finals')
        self.assertEqual(r['loaded'], 1)
        self.assertEqual(self.state(), before)

    def test_reload_replaces_without_changing_anything(self):
        before = self.state()
        self.assertEqual(self.load('ucl_finals', reload=True)['loaded'], 7)
        self.load('ucl_finals', reload=True)
        self.assertEqual(self.state(), before)


if __name__ == '__main__':
    unittest.main()
