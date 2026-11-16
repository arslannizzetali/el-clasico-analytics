"""Unit tests for clasico.events on small hand-built event sequences; no download needed."""
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from clasico.events import game_state, is_clean_receipt, passes_before, possessions, score_before, sec, strip_after, zone  # noqa: E402

BAR, RMA = 'Barcelona', 'Real Madrid'


def ev(i, typ, team=BAR, player=1, t='00:10:00.000', period=1, **extra):
    e = {'id': f'e{i}', 'index': i, 'period': period, 'timestamp': t, 'type': {'name': typ},
         'team': {'name': team}, 'player': {'id': player}, 'location': [50.0, 40.0],
         'possession': extra.pop('possession', 1), 'possession_team': {'name': extra.pop('pteam', team)},
         'play_pattern': {'name': extra.pop('pattern', 'Regular Play')}}
    e.update(extra)
    return e


class TimeAndZone(unittest.TestCase):
    def test_sec(self):
        self.assertEqual(sec({'timestamp': '00:01:02.500'}), 62.5)
        self.assertEqual(sec({'timestamp': '01:00:00.000'}), 3600)

    def test_zone_corners_and_edges(self):
        self.assertEqual(zone(0, 0), 1)          # own third, first lane
        self.assertEqual(zone(119.9, 79.9), 9)   # attacking third, last lane
        self.assertEqual(zone(60, 40), 5)        # centre spot
        self.assertEqual(zone(40, 0), 4)         # x = 40 belongs to the middle third
        self.assertEqual(zone(80, 80 / 3), 8)    # x = 80 attacking third, y = 26.7 middle lane


class Strips(unittest.TestCase):
    def receipt(self, i=0, **kw):
        return ev(i, 'Ball Receipt*', t='00:10:00.000', **kw)

    def test_clean_receipt(self):
        self.assertTrue(is_clean_receipt(self.receipt()))
        self.assertFalse(is_clean_receipt(self.receipt(ball_receipt={'outcome': {'name': 'Incomplete'}})))

    def test_dispossessed_after_carry_is_strip(self):
        seq = [self.receipt(0), ev(1, 'Carry', t='00:10:01.000'), ev(2, 'Dispossessed', t='00:10:02.000')]
        self.assertEqual(strip_after(seq, 0)['id'], 'e2')

    def test_pass_first_is_not_strip(self):
        seq = [self.receipt(0), ev(1, 'Pass', t='00:10:01.000', **{'pass': {}}), ev(2, 'Dispossessed', t='00:10:02.000')]
        self.assertIsNone(strip_after(seq, 0))

    def test_other_players_events_are_skipped(self):
        seq = [self.receipt(0), ev(1, 'Pressure', team=RMA, player=9, t='00:10:00.500'), ev(2, 'Miscontrol', t='00:10:01.000')]
        self.assertEqual(strip_after(seq, 0)['id'], 'e2')

    def test_failed_dribble_is_strip_successful_is_not(self):
        bad = [self.receipt(0), ev(1, 'Dribble', t='00:10:01.000', dribble={'outcome': {'name': 'Incomplete'}})]
        good = [self.receipt(0), ev(1, 'Dribble', t='00:10:01.000', dribble={'outcome': {'name': 'Complete'}})]
        self.assertIsNotNone(strip_after(bad, 0))
        self.assertIsNone(strip_after(good, 0))

    def test_window_and_period_limits(self):
        late = [self.receipt(0), ev(1, 'Dispossessed', t='00:10:12.500')]
        other_half = [self.receipt(0), ev(1, 'Dispossessed', t='00:10:01.000', period=2)]
        self.assertIsNone(strip_after(late, 0))
        self.assertIsNone(strip_after(other_half, 0))


class Possessions(unittest.TestCase):
    def test_groups_by_possession_and_counts_completed_passes(self):
        seq = [ev(0, 'Pass', possession=1, **{'pass': {}}), ev(1, 'Pass', possession=1, **{'pass': {'outcome': {'name': 'Incomplete'}}}),
               ev(2, 'Pass', possession=1, **{'pass': {}}), ev(3, 'Shot', possession=1, shot={}),
               ev(4, 'Pass', team=RMA, possession=2, **{'pass': {}})]
        seqs = possessions(seq)
        self.assertEqual([len(q['es']) for q in seqs], [4, 1])
        self.assertEqual(passes_before(seqs[0]['es'], seq[3]), 2)   # the incomplete pass is not counted


class Score(unittest.TestCase):
    def test_state_before_each_event_includes_own_goals(self):
        goal = {'outcome': {'name': 'Goal'}, 'type': {'name': 'Open Play'}}
        seq = [ev(0, 'Pass', **{'pass': {}}), ev(1, 'Shot', shot=goal), ev(2, 'Pass', **{'pass': {}}),
               ev(3, 'Own Goal For', team=RMA), ev(4, 'Pass', **{'pass': {}})]
        before, final = score_before(seq, (BAR, RMA))
        self.assertEqual(final, {BAR: 1, RMA: 1})
        self.assertEqual(game_state(before[1], BAR, RMA), 'Level')    # the goal event keeps the old score
        self.assertEqual(game_state(before[2], BAR, RMA), 'Ahead')
        self.assertEqual(game_state(before[2], RMA, BAR), 'Behind')
        self.assertEqual(game_state(before[4], BAR, RMA), 'Level')


if __name__ == '__main__':
    unittest.main()
