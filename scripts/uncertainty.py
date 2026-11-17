"""Step 5: bootstrap intervals for period averages and for changes between periods (uncertainty.json).

Each period average rests on 6-8 matches. The unit of resampling is the match (events within a match are
not independent): for every team, period and game state, matches are drawn with replacement and the
metric is recomputed as a ratio of sums, B times. The 5th and 95th percentiles give a 90% interval.
A change between two periods is the difference of independent resamples; if its interval excludes 0,
the change is unlikely to be an artefact of which matches happened to be played.
Input: match_team.json (build.py), game_state.json (game_state.py).
"""
import os
import random
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from clasico import PERIODS, PROCESSED, TEAMS  # noqa: E402
from clasico.output import read_json, read_rows, write_rows  # noqa: E402

OUT = sys.argv[1] if len(sys.argv) > 1 else PROCESSED
RESAMPLES = 5000
SEED = 2021
LEVEL = 0.90
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
    """RESAMPLES resampled values in draw order (not sorted: differences between periods pair draw i with draw i).
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


def main():
    rng = random.Random(SEED)
    match_team = read_json(os.path.join(OUT, 'match_team.json'))
    game_states = read_rows(os.path.join(OUT, 'game_state.json'))
    lo, hi = (1 - LEVEL) / 2, 1 - (1 - LEVEL) / 2
    rows, samples = [], {}
    for metric, (a, b, k, by_state) in METRICS.items():
        for state in (('All', 'Level') if by_state else ('All',)):
            src = match_team if state == 'All' else [g for g in game_states if g['state'] == state]
            for team in TEAMS:
                for p in PERIODS:
                    rs = [r for r in src if r['team'] == team and r['period'] == p]
                    s = boot(rs, a, b, k, rng)
                    samples[(metric, state, team, p)] = s
                    rows.append(dict(key=f'{metric}|{state}|{team}|{p}', kind='period', metric=metric, state=state,
                                     team=team, period=p, matches=len(rs), value=round(ratio(rs, a, b, k), 2),
                                     lo=round(pct(s, lo), 2), hi=round(pct(s, hi), 2)))
                for i, p1 in enumerate(PERIODS):
                    for p2 in PERIODS[i + 1:]:
                        s1, s2 = samples[(metric, state, team, p1)], samples[(metric, state, team, p2)]
                        d = [y - x for x, y in zip(s1, s2)]   # independent draws, paired by index
                        v1 = next(r['value'] for r in rows if r['key'] == f'{metric}|{state}|{team}|{p1}')
                        v2 = next(r['value'] for r in rows if r['key'] == f'{metric}|{state}|{team}|{p2}')
                        dlo, dhi = pct(d, lo), pct(d, hi)
                        rows.append(dict(key=f'{metric}|{state}|{team}|{p1}>{p2}', kind='change', metric=metric,
                                         state=state, team=team, period=f'{p1}>{p2}', matches=None,
                                         value=round(v2 - v1, 2), lo=round(dlo, 2), hi=round(dhi, 2),
                                         clear=1 if dlo > 0 or dhi < 0 else 0))
    write_rows(os.path.join(OUT, 'uncertainty.json'), rows, os.path.abspath(__file__))
    clear = sum(r['clear'] for r in rows if r['kind'] == 'change')
    total = sum(1 for r in rows if r['kind'] == 'change')
    print(f'uncertainty: {len(rows)} rows, {RESAMPLES} resamples, {LEVEL:.0%} intervals; '
          f'{clear}/{total} period changes clear of zero')


if __name__ == '__main__':
    main()
