"""90% bootstrap intervals for the league-wide tables (run analysis/league.py first; no database needed).

    python3 analysis/intervals.py

Input: data/league/match_team_*.csv. Output: data/league/finals.csv (below) and data/league/intervals.csv,
three kinds of row:

  period    a metric for one group of matches in one period, with its interval
  change    the same group between two periods
  contrast  two groups in the same period: is a Clásico different from Barcelona's other matches?

Groups are Barcelona's league matches split by opponent, so they do not overlap and the contrasts compare
independent samples: Real Madrid (the Clásicos), the other top-10 clubs, every other club. Each is seen from
both sides (Barcelona, and the opponent).

finals.csv sets every Champions League final against the team's own league football that season: Barcelona's
league matches of the same season; for Real Madrid the 2015/16 season when it is the final's season, otherwise
the Clásicos of the same period (the only Real Madrid league matches in the data). A final is one match, so it
is compared with single matches, not with an average: `pct_below` is the share of baseline matches with a lower
value, and `unusual` marks a final outside the middle 90% of those matches (below the 5th or above the 95th
percentile). The baseline average and its interval are given for reference.

Two special seasons are split by coach: Barcelona 2007/08 (Rijkaard)
against 2008/09 (Guardiola's first season), and Real Madrid 2015/16 (Benítez, then Zidane).
"""
import os
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from clasico import ROOT  # noqa: E402
from clasico.bootstrap import SEED, interval, percentile, ratio, resample  # noqa: E402

LEAGUE = os.path.join(ROOT, 'data', 'league')
PERIODS = ('2004-09', '2009-13', '2013-17', '2017-21')
GROUPS = ('Real Madrid', 'Top-10 club', 'Other club')
CONTRASTS = (('Real Madrid', 'Other club'), ('Real Madrid', 'Top-10 club'), ('Top-10 club', 'Other club'))
# metric: (numerator, denominator, scale). 'one' counts matches, so num/one is a per-match average.
METRICS = {
    'passes_per_shot': ('passes_before_shot_sum', 'open_play_shots', 1),
    'press_success_pct': ('pressures_won_5s', 'pressures', 100),
    'ppda': ('opp_buildup_passes', 'def_actions', 1),
    'possession_pct': ('possession_pct', 'one', 1),
    'pass_interval_s': ('pass_interval_s', 'one', 1),
    'attack_speed_mps': ('attack_speed_mps', 'one', 1),
    'np_xg': ('np_xg', 'one', 1),
}


def barcelona_groups(top):
    """Barcelona's league matches, one row per side, labelled by the kind of opponent."""
    d = pd.read_csv(os.path.join(LEAGUE, 'match_team_barcelona_all.csv'))
    opponent_of_barca = d.loc[d['team'] != 'Barcelona'].set_index('match_id')['team']
    d['opponent_club'] = d['match_id'].map(opponent_of_barca)
    d['group'] = np.where(d['opponent_club'] == 'Real Madrid', 'Real Madrid',
                          np.where(d['opponent_club'].isin(top), 'Top-10 club', 'Other club'))
    d['side'] = np.where(d['team'] == 'Barcelona', 'Barcelona', 'Opponent')
    return d


def rows_for(d, keys, rng):
    """Period rows for every combination of keys (+ period), and the samples behind them."""
    out, samples = [], {}
    for k, g in d.groupby(keys + ['period']):
        for metric, (a, b, scale) in METRICS.items():
            g2 = g.dropna(subset=[a])
            if g2.empty:
                continue
            s = resample(g2[a], g2[b], scale, rng)
            samples[(*k, metric)] = s
            lo, hi = interval(s)
            out.append(dict(kind='period', **dict(zip(keys + ['period'], k)), metric=metric, matches=len(g2),
                            value=round(ratio(g2[a].to_numpy(float), g2[b].to_numpy(float), scale), 2),
                            lo=round(lo, 2), hi=round(hi, 2)))
    return out, samples


def diff_row(kind, s1, s2, v1, v2, **labels):
    d = s2 - s1
    lo, hi = interval(d)
    return dict(kind=kind, **labels, value=round(v2 - v1, 2), lo=round(lo, 2), hi=round(hi, 2),
                clear=int(lo > 0 or hi < 0))


SPECIAL = (
    # group, team, (before coach, after coach), label of the difference
    ('Barcelona 2007-09', 'Barcelona', ('Frank Rijkaard', 'Pep Guardiola'), 'Guardiola - Rijkaard'),
    ('Real Madrid 2015/16', 'Real Madrid', ('Rafael Benítez', 'Zinédine Zidane'), 'Zidane - Benítez'),
)


def special_seasons(barca, rng):
    """Before/after a new coach: Barcelona 2007/08 vs 2008/09, Real Madrid 2015/16 before and after January."""
    rm = pd.read_csv(os.path.join(LEAGUE, 'match_team_season_2015_16.csv'))
    src = {'Barcelona': barca[barca['season_name'].isin(['2007/2008', '2008/2009'])],
           'Real Madrid': rm.assign(one=1)}
    out = []
    for group, team, coaches, label in SPECIAL:
        t = src[team]
        t = t[(t['team'] == team) & t['coach'].isin(coaches)].assign(group=group, side=t['coach'], period='special')
        r, S = rows_for(t, ['group', 'side'], rng)
        out += r
        v = {(x['side'], x['metric']): x['value'] for x in r}
        for metric in METRICS:
            k = [(group, c, 'special', metric) for c in coaches]
            out.append(diff_row('contrast', S[k[0]], S[k[1]], v[(coaches[0], metric)], v[(coaches[1], metric)],
                                group=label, side=team, period='special', metric=metric))
    return out


def finals_vs_baseline(rng):
    fin = pd.read_csv(os.path.join(LEAGUE, 'match_team_ucl_finals.csv'))
    barca = pd.read_csv(os.path.join(LEAGUE, 'match_team_barcelona_all.csv'))
    s1516 = pd.read_csv(os.path.join(LEAGUE, 'match_team_season_2015_16.csv'))
    clasico = pd.read_csv(os.path.join(LEAGUE, 'match_team_clasico.csv'))
    out = []
    for _, f in fin[fin['team'].isin(['Barcelona', 'Real Madrid'])].iterrows():
        if f['team'] == 'Barcelona':
            base, basis = barca[(barca['team'] == 'Barcelona') & (barca['season_name'] == f['season_name'])], 'La Liga, same season'
        elif f['season_name'] == '2015/2016':
            base, basis = s1516[s1516['team'] == 'Real Madrid'], 'La Liga, same season'
        else:
            base, basis = clasico[(clasico['team'] == 'Real Madrid') & (clasico['period'] == f['period'])], f"Clásicos {f['period']}"
        base = base.assign(one=1)
        for metric, (a, b, scale) in METRICS.items():
            g = base.dropna(subset=[a])
            value = scale * f[a] / f[b] if b != 'one' and f[b] > 0 else (f[a] if b == 'one' else np.nan)
            lo, hi = interval(resample(g[a], g[b], scale, rng))
            per_match = (scale * g[a] / g[b].where(g[b] > 0)).dropna().to_numpy() if b != 'one' else g[a].to_numpy(float)
            p5, p95 = percentile(per_match, 0.05), percentile(per_match, 0.95)
            out.append(dict(match_id=f['match_id'], match_date=f['match_date'], season_name=f['season_name'], team=f['team'],
                            opponent=f['opponent'], metric=metric, value=round(value, 2),
                            baseline=round(ratio(g[a].to_numpy(float), g[b].to_numpy(float), scale), 2),
                            lo=round(lo, 2), hi=round(hi, 2), match_p5=round(p5, 2), match_p95=round(p95, 2),
                            pct_below=round(100 * (per_match < value).mean()), baseline_matches=len(g), basis=basis,
                            unusual=int(value < p5 or value > p95)))
    pd.DataFrame(out).to_csv(os.path.join(LEAGUE, 'finals.csv'), index=False)
    print(f"finals: {len(out) // len(METRICS)} finals, {sum(r['unusual'] for r in out)}/{len(out)} metrics outside the middle 90% of baseline matches")


def main():
    rng = np.random.default_rng(SEED)
    top = set(pd.read_csv(os.path.join(ROOT, 'data', 'reference', 'standings.csv'))
              .assign(t10=lambda s: s['position'] <= 10).groupby('team_name')
              .agg(n=('t10', 'sum'), avg=('position', 'mean')).sort_values(['n', 'avg'], ascending=[False, True])
              .head(10).index)
    d = barcelona_groups(top).assign(one=1)
    rows, S = rows_for(d, ['group', 'side'], rng)
    value = {(r['group'], r['side'], r['period'], r['metric']): r['value'] for r in rows}

    for g in GROUPS:
        for side in ('Barcelona', 'Opponent'):
            for metric in METRICS:
                for i, p1 in enumerate(PERIODS):
                    for p2 in PERIODS[i + 1:]:
                        k1, k2 = (g, side, p1, metric), (g, side, p2, metric)
                        if k1 in S and k2 in S:
                            rows.append(diff_row('change', S[k1], S[k2], value[k1], value[k2], group=g, side=side,
                                                 period=f'{p1}>{p2}', metric=metric))
    for g1, g2 in CONTRASTS:
        for side in ('Barcelona', 'Opponent'):
            for p in PERIODS:
                for metric in METRICS:
                    k1, k2 = (g2, side, p, metric), (g1, side, p, metric)
                    if k1 in S and k2 in S:   # value = g1 - g2, e.g. Clásicos minus matches against other clubs
                        rows.append(diff_row('contrast', S[k1], S[k2], value[k1], value[k2], group=f'{g1} - {g2}',
                                             side=side, period=p, metric=metric))

    rows += special_seasons(d, rng)

    finals_vs_baseline(rng)

    out = pd.DataFrame(rows)
    out['matches'] = out['matches'].astype('Int64')
    out['clear'] = out['clear'].astype('Int64')
    out.to_csv(os.path.join(LEAGUE, 'intervals.csv'), index=False)
    for kind in ('change', 'contrast'):
        k = out[out['kind'] == kind]
        print(f'{kind}: {int(k["clear"].sum())}/{len(k)} clear of zero')
    print(f'intervals: {len(out)} rows -> data/league/intervals.csv')


if __name__ == '__main__':
    main()
