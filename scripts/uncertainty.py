"""Step 5: bootstrap intervals for group averages and for changes between groups (uncertainty.json).

Matches are grouped two ways: by four-season period (2005-09 ... 2017-21) and by Barcelona's coach.
Each group average rests on few matches. The unit of resampling is the match (events within a match are
not independent): for every grouping, team, group and game state, matches are drawn with replacement and the
metric is recomputed as a ratio of sums, RESAMPLES times. The 5th and 95th percentiles give a 90% interval.
A change between two groups is the difference of independent resamples; if its interval excludes 0,
the change is unlikely to be an artefact of which matches happened to be played.

Leave-one-out: for every group average, each match is dropped in turn and the average recomputed; loo_lo and
loo_hi are the lowest and highest of those values and loo_date is the match whose removal moves it most. A group
is flagged single_match=1 when dropping one match moves its average by more than LOO_FLAG (20%). For a change, the
same is done over the matches of both groups; loo_flip=1 when dropping one match can bring the change to zero or
reverse its sign.

Coach groups with fewer than MIN_MATCHES matches (Vilanova, Martino, Setién, Koeman) get a row with their
average but no interval and no change test: with one or two matches a resample can only repeat those matches,
so the "interval" would be the spread of two numbers, not a statement about uncertainty.
Input: match_team.json (build.py), game_state.json (game_state.py).
"""
import os
import random
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from clasico import COACH_GROUPS, PERIODS, PROCESSED, TEAMS  # noqa: E402
from clasico.output import read_json, read_rows, write_rows  # noqa: E402

OUT = sys.argv[1] if len(sys.argv) > 1 else PROCESSED
RESAMPLES = 5000
SEED = 2021
LEVEL = 0.90
MIN_MATCHES = 4   # smallest group that gets an interval and enters change tests
LOO_FLAG = 0.20   # relative move of a group average, when one match is dropped, that marks it as fragile
# grouping: (field in match_team / game_state, groups in chronological order)
GROUPINGS = {
    'period': ('period', PERIODS),
    'coach': ('coach_group', COACH_GROUPS),
}
# metric: (numerator, denominator, scale, available by game state)
METRICS = {
    'passes_per_shot': ('passes_before_shot_sum', 'open_play_shots', 1, True),
    'press_success_pct': ('pressures_won_5s', 'pressures', 100, True),
    'stripped_per100': ('balls_stripped', 'opp_controls', 100, True),
    'ppda': ('opp_buildup_passes', 'def_actions', 1, True),
    'conceded_shot_15s_pct': ('conceded_shot_15s', 'turnovers', 100, False),
}


def ratio(rows, a, b, k):
    den = sum(r[b] for r in rows)
    return k * sum(r[a] for r in rows) / den if den else None


def boot(rows, a, b, k, rng):
    """RESAMPLES resampled values in draw order (not sorted: differences between groups pair draw i with draw i).
    A resample with an empty denominator keeps the observed value, so both lists stay length RESAMPLES."""
    obs = ratio(rows, a, b, k)
    out = []
    for _ in range(RESAMPLES):
        v = ratio([rng.choice(rows) for _ in rows], a, b, k)
        out.append(obs if v is None else v)
    return out


def pct(vals, q):
    s = sorted(vals)
    return s[min(len(s) - 1, max(0, round(q * (len(s) - 1))))]


def leave_one_out(rows, a, b, k):
    """[(date of the dropped match, average without it)] for every match whose removal leaves a denominator."""
    out = []
    for i, dropped in enumerate(rows):
        v = ratio(rows[:i] + rows[i + 1:], a, b, k)
        if v is not None:
            out.append((dropped['date'], v))
    return out


def key(metric, state, team, group):
    return f'{metric}|{state}|{team}|{group}'


def group_row(grouping, metric, state, team, group, rs, a, b, k, samples):
    row = dict(key=key(metric, state, team, group), kind='group', grouping=grouping, metric=metric, state=state,
               team=team, group=group, matches=len(rs), value=round(ratio(rs, a, b, k), 2), lo=None, hi=None)
    if samples is not None:
        lo, hi = (1 - LEVEL) / 2, 1 - (1 - LEVEL) / 2
        row.update(lo=round(pct(samples, lo), 2), hi=round(pct(samples, hi), 2))
        value = ratio(rs, a, b, k)
        loo = leave_one_out(rs, a, b, k)
        date, worst = max(loo, key=lambda dv: abs(dv[1] - value))
        row.update(loo_lo=round(min(v for _, v in loo), 2), loo_hi=round(max(v for _, v in loo), 2), loo_date=date,
                   single_match=1 if value and abs(worst - value) / abs(value) > LOO_FLAG else 0)
    return row


def change_row(grouping, metric, state, team, g1, g2, v1, v2, s1, s2, loo1, loo2):
    lo, hi = (1 - LEVEL) / 2, 1 - (1 - LEVEL) / 2
    diffs = [y - x for x, y in zip(s1, s2)]   # independent draws, paired by index
    dlo, dhi = pct(diffs, lo), pct(diffs, hi)
    return dict(key=key(metric, state, team, f'{g1}>{g2}'), kind='change', grouping=grouping, metric=metric,
                state=state, team=team, group=f'{g1}>{g2}', matches=None,
                value=round(v2 - v1, 2), lo=round(dlo, 2), hi=round(dhi, 2),
                clear=1 if dlo > 0 or dhi < 0 else 0, **change_loo(v1, v2, loo1, loo2))


def change_loo(v1, v2, loo1, loo2):
    """Range of the change when one match (from either group) is dropped."""
    changes = [v2 - x for _, x in loo1] + [y - v1 for _, y in loo2]
    lo, hi = min(changes), max(changes)
    flip = (v2 - v1 > 0 and lo <= 0) or (v2 - v1 < 0 and hi >= 0)
    return dict(loo_lo=round(lo, 2), loo_hi=round(hi, 2), loo_flip=1 if flip else 0)


def main():
    rng = random.Random(SEED)
    match_team = read_json(os.path.join(OUT, 'match_team.json'))
    game_states = read_rows(os.path.join(OUT, 'game_state.json'))
    rows = []
    for grouping, (field, groups) in GROUPINGS.items():
        for metric, (a, b, k, by_state) in METRICS.items():
            for state in (('All', 'Level') if by_state else ('All',)):
                src = match_team if state == 'All' else [g for g in game_states if g['state'] == state]
                for team in TEAMS:
                    samples, values, loo = {}, {}, {}
                    for group in groups:
                        rs = [r for r in src if r['team'] == team and r[field] == group]
                        if len(rs) >= MIN_MATCHES:
                            samples[group] = boot(rs, a, b, k, rng)
                            loo[group] = leave_one_out(rs, a, b, k)
                        row = group_row(grouping, metric, state, team, group, rs, a, b, k, samples.get(group))
                        values[group] = row['value']
                        rows.append(row)
                    tested = [g for g in groups if g in samples]
                    for i, g1 in enumerate(tested):
                        for g2 in tested[i + 1:]:
                            rows.append(change_row(grouping, metric, state, team, g1, g2, values[g1], values[g2],
                                                   samples[g1], samples[g2], loo[g1], loo[g2]))
    write_rows(os.path.join(OUT, 'uncertainty.json'), rows, os.path.abspath(__file__))
    for grouping in GROUPINGS:
        changes = [r for r in rows if r['kind'] == 'change' and r['grouping'] == grouping]
        clear = sum(r['clear'] for r in changes)
        fragile = sum(r.get('single_match', 0) for r in rows if r['kind'] == 'group' and r['grouping'] == grouping)
        flips = sum(r['loo_flip'] for r in changes if r['clear'])
        print(f'uncertainty ({grouping}): {clear}/{len(changes)} changes clear of zero at {LEVEL:.0%}, '
              f'{flips} of them reversed or zeroed by dropping one match; {fragile} averages moved >20% by one match')
    print(f'uncertainty: {len(rows)} rows, {RESAMPLES} resamples')


if __name__ == '__main__':
    main()
