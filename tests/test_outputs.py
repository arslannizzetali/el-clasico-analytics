"""data/processed çıktıları için tutarlılık testleri. Önce `python3 pipeline.py` çalıştırılmış olmalı;
çıktılar yoksa testler atlanır."""
import collections
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from clasico import PROCESSED, TEAMS  # noqa: E402
from clasico.events import zone  # noqa: E402
from clasico.output import read_json, read_rows  # noqa: E402

P = lambda name: os.path.join(PROCESSED, name)  # noqa: E731
READY = all(os.path.exists(P(f)) for f in ('match_team.json', 'shots.json', 'losses_ds.json', 'strips.json', 'game_state.json'))


@unittest.skipUnless(READY, 'önce pipeline.py çalıştırılmalı')
class Outputs(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.M = read_json(P('match_team.json'))
        cls.S = read_json(P('shots.json'))
        cls.L = read_rows(P('losses_ds.json'))
        cls.ST = read_json(P('strips.json'))
        cls.G = read_rows(P('game_state.json'))

    def test_29_matches_two_rows_each(self):
        self.assertEqual(len({m['match_id'] for m in self.M}), 29)
        self.assertEqual(collections.Counter(m['match_id'] for m in self.M).most_common(1)[0][1], 2)
        self.assertEqual(collections.Counter(m['period'] for m in self.M if m['team'] == 'Barcelona'),
                         {'2005-09': 6, '2009-13': 8, '2013-17': 8, '2017-21': 7})

    def test_scores_are_mirrored(self):
        by = {(m['match_id'], m['team']): m for m in self.M}
        for (mid, t), m in by.items():
            o = by[(mid, 'Real Madrid' if t == 'Barcelona' else 'Barcelona')]
            self.assertEqual((m['goals_for'], m['goals_against']), (o['goals_against'], o['goals_for']))

    def test_passes_per_shot_uses_first_shots_only(self):
        first = collections.Counter((s['match_id'], s['team']) for s in self.S if s['first_in_attack'] and s['open_play'])
        for m in self.M:
            self.assertEqual(m['open_play_shots'], first[(m['match_id'], m['team'])])

    def test_shot_goals_do_not_exceed_score(self):
        g = collections.Counter((s['match_id'], s['team']) for s in self.S if s['outcome'] == 'Gol')
        for m in self.M:
            self.assertLessEqual(g[(m['match_id'], m['team'])], m['goals_for'])   # penaltı ve kendi kalesine gol listede yok

    def test_rates_are_in_range(self):
        for m in self.M:
            for f in ('press_success_pct', 'conceded_shot_15s_pct', 'regained_8s_pct', 'stripped_per100'):
                self.assertTrue(0 <= m[f] <= 100, (m['key'], f, m[f]))

    def test_losses_and_strips_line_up(self):
        self.assertEqual(len(self.L), len(self.ST))
        for l, s in zip(self.L, self.ST):
            self.assertEqual((l['match'], l['team'], l['player']), (s['mac'], s['topu_kaptiran_takim'], s['oyuncu']))
            self.assertEqual(zone(l['x'], l['y']), s['bolge'])

    def test_strip_totals_match_metric(self):
        n = collections.Counter((l['match_id'], l['team']) for l in self.L)
        for m in self.M:
            # takımın söktüğü top = rakibin kontrolden sonra kaptırdığı top
            self.assertEqual(m['balls_stripped'], n[(m['match_id'], m['opponent'])])

    def test_loss_shot_fields(self):
        for l in self.L:
            self.assertEqual(l['shot'] == 1, l['shot_x'] is not None)
            if l['goal']:
                self.assertEqual(l['result'], 'Gol')

    def test_game_state_partitions_matches(self):
        F = ('open_play_shots', 'passes_before_shot_sum', 'pressures', 'pressures_won_5s', 'opp_buildup_passes', 'def_actions', 'opp_controls', 'balls_stripped')
        tot = collections.defaultdict(collections.Counter)
        mins = collections.Counter()
        for r in self.G:
            mins[(r['match_id'], r['team'])] += r['minutes']
            for f in F:
                tot[(r['match_id'], r['team'])][f] += r[f]
        for m in self.M:
            for f in F:
                self.assertEqual(tot[(m['match_id'], m['team'])][f], m[f], (m['key'], f))
            self.assertTrue(85 <= mins[(m['match_id'], m['team'])] <= 105)
        g = {(r['match_id'], r['team'], r['state']): r['minutes'] for r in self.G}
        for mid in {m['match_id'] for m in self.M}:
            self.assertAlmostEqual(g[(mid, TEAMS[0], 'Önde')], g[(mid, TEAMS[1], 'Geride')], delta=0.05)


if __name__ == '__main__':
    unittest.main()
