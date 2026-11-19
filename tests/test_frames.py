"""The pandas + PostgreSQL metrics (clasico/frames.py) must give the reference pipeline's numbers on the Clásicos.

Needs requirements.txt and a database loaded with `python3 scripts/load_db.py clasico`; skipped otherwise."""
import csv
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from clasico import PROCESSED  # noqa: E402

try:
    from clasico import db, frames
    with db.connect() as _c:
        READY = _c.execute("SELECT count(*) FROM match_categories WHERE category = 'clasico'").fetchone()[0] == 29
except Exception:  # pandas/psycopg missing, database down or not loaded
    READY = False
if os.environ.get('REQUIRE_DB') and not READY:   # set in CI, so the test cannot pass by being skipped
    raise RuntimeError('REQUIRE_DB is set but the database is not loaded')

EXACT = ('goals_for', 'goals_against', 'passes', 'open_play_shots', 'passes_before_shot_sum', 'direct_shots',
         'long_shots', 'pressures', 'pressures_won_5s', 'opp_passes', 'opp_buildup_passes', 'def_actions')
ROUNDED = ('passes_per_shot', 'press_success_pct', 'ppda')   # one decimal; allow last-digit rounding differences


@unittest.skipUnless(READY, 'needs requirements.txt and `scripts/load_db.py clasico`')
class SameAsReference(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        with open(os.path.join(PROCESSED, 'match_team.csv'), encoding='utf-8') as fh:
            cls.ref = {(int(r['match_id']), r['team']): r for r in csv.DictReader(fh)}
        ev, ms = frames.load('clasico', db.engine())
        cls.new = {(r.match_id, r.team): r for r in frames.match_team(ev, ms).itertuples()}

    def test_same_match_teams(self):
        self.assertEqual(set(self.ref), set(self.new))

    def test_counts_identical(self):
        for k, r in self.ref.items():
            for c in EXACT:
                self.assertEqual(int(r[c]), int(getattr(self.new[k], c)), f'{k} {c}')

    def test_ratios_match(self):
        for k, r in self.ref.items():
            for c in ROUNDED:
                if r[c] == '':
                    continue
                self.assertAlmostEqual(float(r[c]), float(getattr(self.new[k], c)), delta=0.051, msg=f'{k} {c}')

    def test_formations_identical(self):
        for k, r in self.ref.items():
            self.assertEqual(r['formation'], self.new[k].formation, k)


if __name__ == '__main__':
    unittest.main()
