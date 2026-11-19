"""The pandas metrics (clasico/frames.py) must equal the reference code (scripts/build.py match_rows) on matches
the reference pipeline never ran on: the Champions League finals, with other opponents and extra time.

Needs requirements.txt and a database with `scripts/load_db.py ucl_finals`; skipped otherwise."""
import importlib.util
import os
import sys
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
from clasico import data  # noqa: E402

try:
    from clasico import db, frames
    with db.connect() as _c:
        READY = _c.execute("SELECT count(*) FROM match_categories WHERE category = 'ucl_finals'").fetchone()[0] == 7
except Exception:  # pandas/psycopg missing, database down or not loaded
    READY = False
if os.environ.get('REQUIRE_DB') and not READY:
    raise RuntimeError('REQUIRE_DB is set but the finals are not loaded')

EXACT = ('passes', 'open_play_shots', 'passes_before_shot_sum', 'direct_shots', 'long_shots', 'pressures',
         'pressures_won_5s', 'opp_passes', 'opp_buildup_passes', 'def_actions')


def reference_rows():
    """match_rows from scripts/build.py, unchanged; it pairs the two teams through its module-level OPP."""
    spec = importlib.util.spec_from_file_location('build', os.path.join(ROOT, 'scripts', 'build.py'))
    build = importlib.util.module_from_spec(spec)
    argv, sys.argv = sys.argv, sys.argv[:1]
    try:
        spec.loader.exec_module(build)
    finally:
        sys.argv = argv
    out = {}
    for g in data.ucl_finals():
        h, a = g['home_team']['home_team_name'], g['away_team']['away_team_name']
        build.OPP = {h: a, a: h}
        for r in build.match_rows(dict(g, season=g['season']['season_name']), data.events(g['match_id']), []):
            out[(r['match_id'], r['team'])] = r
    return out


@unittest.skipUnless(READY, 'needs requirements.txt and `scripts/load_db.py ucl_finals`')
class FinalsSameAsReference(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.ref = reference_rows()
        eng = db.engine()
        try:
            ev, ms = frames.load('ucl_finals', eng)
        finally:
            eng.dispose()
        cls.new = {(r.match_id, r.team): r for r in frames.match_team(ev, ms).itertuples()}

    def test_fourteen_team_rows(self):
        self.assertEqual(len(self.ref), 14)
        self.assertEqual(set(self.ref), set(self.new))

    def test_counts_identical(self):
        for k, r in self.ref.items():
            for c in EXACT:
                self.assertEqual(int(r[c]), int(getattr(self.new[k], c)), f'{k} {c}')

    def test_formations_identical(self):
        for k, r in self.ref.items():
            self.assertEqual(r['formation'], self.new[k].formation, k)


if __name__ == '__main__':
    unittest.main()
