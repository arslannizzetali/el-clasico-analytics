"""The numpy bootstrap (clasico/bootstrap.py) must agree with the reference (scripts/uncertainty.py) on the
Clásicos. Random draws differ between the two, so intervals are compared with a Monte Carlo tolerance.
Needs numpy and pandas; reads data/league/match_team_clasico.csv (no database)."""
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from clasico import PROCESSED, ROOT  # noqa: E402
from clasico.output import read_rows  # noqa: E402

try:
    import numpy as np
    import pandas as pd
    from clasico.bootstrap import SEED, interval, percentile, ratio, resample
    READY = True
except ImportError:
    READY = False

CSV = os.path.join(ROOT, 'data', 'league', 'match_team_clasico.csv')
METRICS = {'passes_per_shot': ('passes_before_shot_sum', 'open_play_shots', 1),
           'press_success_pct': ('pressures_won_5s', 'pressures', 100),
           'ppda': ('opp_buildup_passes', 'def_actions', 1)}
PERIOD = {'2004-09': '2005-09'}   # the league tables start in 2004/05; the Clásicos in the data start in 2005/06


@unittest.skipUnless(READY and os.path.exists(CSV), 'needs requirements.txt and analysis/league.py')
class SameAsReference(unittest.TestCase):
    def test_intervals_match_reference(self):
        ref = {r['key']: r for r in read_rows(os.path.join(PROCESSED, 'uncertainty.json'))}
        d = pd.read_csv(CSV)
        rng = np.random.default_rng(SEED)
        n = 0
        for (team, period), g in d.groupby(['team', 'period']):
            for m, (a, b, k) in METRICS.items():
                r = ref[f"{m}|All|{team}|{PERIOD.get(period, period)}"]
                self.assertEqual(r['matches'], len(g))
                self.assertAlmostEqual(r['value'], ratio(g[a].to_numpy(float), g[b].to_numpy(float), k), delta=0.006)
                lo, hi = interval(resample(g[a], g[b], k, rng))
                tol = 0.06 * (r['hi'] - r['lo']) + 0.02   # Monte Carlo error of a 5,000-draw percentile
                self.assertAlmostEqual(r['lo'], lo, delta=tol, msg=f'{team} {period} {m} lo')
                self.assertAlmostEqual(r['hi'], hi, delta=tol, msg=f'{team} {period} {m} hi')
                n += 1
        self.assertEqual(n, 24)

    def test_percentile_rule(self):
        s = np.arange(101, dtype=float)
        self.assertEqual(percentile(s, 0.05), 5.0)
        self.assertEqual(percentile(s, 0.95), 95.0)

    def test_empty_denominator_keeps_observed_value(self):
        s = resample([1, 0], [2, 0], 1, np.random.default_rng(0), b=200)
        self.assertEqual(len(s), 200)
        self.assertTrue(np.all(s == 0.5))


if __name__ == '__main__':
    unittest.main()
