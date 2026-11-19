"""A clean, tidy CSV set for Power BI / Tableau (star schema), from the committed outputs; no database needed.

    python3 analysis/export_bi.py

Input: data/processed (reference pipeline), data/league (analysis/league.py, intervals.py), data/reference.
Output: data/bi/*.csv, UTF-8, comma-separated, ISO dates, one header row, no index. See docs/bi.md for the model,
the relationships and ready-made measures.

Rates (PPDA, press success, passes per shot) are NOT averaged per match in a BI tool: the fact table carries the
numerator and denominator of each, so a measure can be SUM(numerator) / SUM(denominator) for any filter, exactly as
the project computes them.
"""
import json
import os
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from clasico import PROCESSED, ROOT  # noqa: E402
from clasico.log import get_logger  # noqa: E402

LEAGUE = os.path.join(ROOT, 'data', 'league')
OUT = os.path.join(ROOT, 'data', 'bi')
CATS = ('clasico', 'barcelona_vs_top10', 'barcelona_all', 'season_2015_16', 'ucl_finals')
log = get_logger('export_bi')


def match_team():
    """Every team-match row once, with the categories of its match as flags."""
    frames, member = [], []
    for cat in CATS:
        d = pd.read_csv(os.path.join(LEAGUE, f'match_team_{cat}.csv'))
        frames.append(d)
        member.append(pd.DataFrame({'match_id': d['match_id'].unique(), 'category': cat}))
    mt = pd.concat(frames).drop_duplicates(['match_id', 'team']).reset_index(drop=True)
    flags = pd.concat(member).drop_duplicates().assign(v=1).pivot(index='match_id', columns='category', values='v')
    flags = flags.reindex(columns=list(CATS)).notna()
    return mt, flags


def main():
    os.makedirs(OUT, exist_ok=True)
    mt, flags = match_team()
    standings = pd.read_csv(os.path.join(ROOT, 'data', 'reference', 'standings.csv'))

    # dim_team: every club in the data, with its league record 2004/05-2020/21 where it has one
    rec = standings.groupby('team_name').agg(seasons_in_la_liga=('position', 'size'),
                                             top10_finishes=('position', lambda p: int((p <= 10).sum())),
                                             avg_final_position=('position', 'mean')).round({'avg_final_position': 1})
    top = rec.sort_values(['top10_finishes', 'avg_final_position'], ascending=[False, True]).head(10).index
    teams = pd.DataFrame({'team': sorted(set(mt['team']) | set(rec.index))})
    dim_team = teams.join(rec, on='team')
    dim_team['is_top10_club'] = dim_team['team'].isin(top)
    dim_team['seasons_in_la_liga'] = dim_team['seasons_in_la_liga'].astype('Int64')
    dim_team['top10_finishes'] = dim_team['top10_finishes'].astype('Int64')

    # dim_match: one row per match
    home = mt[mt['venue'] == 'Home'].set_index('match_id')
    away = mt[mt['venue'] == 'Away'].set_index('match_id')
    neutral = mt[~mt['match_id'].isin(home.index)].sort_values(['match_id', 'team']).groupby('match_id')
    h_team = pd.concat([home['team'], neutral['team'].first()])
    a_team = pd.concat([away['team'], neutral['team'].last()])
    first = mt.drop_duplicates('match_id').set_index('match_id')
    dim_match = pd.DataFrame({
        'match_id': first.index,
        'match_date': first['match_date'].values,
        'season': first['season_name'].values,
        'period': first['period'].values,
        'competition': np.where(flags.loc[first.index, 'ucl_finals'], 'Champions League final', 'La Liga'),
        'home_team': h_team.reindex(first.index).values,
        'away_team': a_team.reindex(first.index).values,
    })
    goals = mt.set_index(['match_id', 'team'])['goals_for']
    dim_match['home_goals'] = [goals[(m, t)] for m, t in zip(dim_match['match_id'], dim_match['home_team'])]
    dim_match['away_goals'] = [goals[(m, t)] for m, t in zip(dim_match['match_id'], dim_match['away_team'])]
    for cat in CATS:
        dim_match['is_' + cat] = flags.loc[dim_match['match_id'], cat].values
    dim_match = dim_match.sort_values(['match_date', 'match_id'])

    # fact_match_team: raw counts (sum them) and per-match values (for match-level charts)
    f = mt.rename(columns={'season_name': 'season', 'goals_for': 'goals_for', 'np_xg': 'np_xg'})
    f['points'] = np.select([f['goals_for'] > f['goals_against'], f['goals_for'] == f['goals_against']], [3, 1], 0)
    f['is_top10_opponent'] = f['opponent'].isin(top)
    cols = ['match_id', 'team', 'opponent', 'venue', 'coach', 'formation', 'formation_changes', 'goals_for',
            'goals_against', 'points', 'is_top10_opponent',
            'passes', 'open_play_shots', 'passes_before_shot_sum', 'pressures', 'pressures_won_5s',
            'opp_buildup_passes', 'def_actions', 'shots', 'np_xg',
            'passes_per_shot', 'press_success_pct', 'ppda', 'possession_pct', 'pass_interval_s', 'attack_speed_mps']
    fact = f[cols].sort_values(['match_id', 'team'])

    # intervals: the Clásico ones (reference pipeline) and the league ones, in one long table
    u = pd.DataFrame(json.load(open(os.path.join(PROCESSED, 'uncertainty.json'), encoding='utf-8'))['rows'])
    u = u.assign(source='clasico_reference', group='Clásico', side=u['team']).drop(columns=['key', 'team'])
    li = pd.read_csv(os.path.join(LEAGUE, 'intervals.csv')).assign(source='league', state='All')
    keep = ['source', 'kind', 'group', 'side', 'state', 'period', 'metric', 'matches', 'value', 'lo', 'hi', 'clear']
    intervals = pd.concat([u[keep], li[keep]])
    intervals['matches'] = intervals['matches'].astype('Int64')
    intervals['clear'] = intervals['clear'].map({1: True, 0: False, 1.0: True, 0.0: False}).astype('boolean')

    out = {
        'dim_match': dim_match, 'dim_team': dim_team, 'standings': standings.rename(columns={'season_name': 'season', 'team_name': 'team'}),
        'fact_match_team': fact, 'fact_intervals': intervals,
        'fact_finals': pd.read_csv(os.path.join(LEAGUE, 'finals.csv')).drop(columns=['match_date', 'season_name']),
        'clasico_match_team': pd.read_csv(os.path.join(PROCESSED, 'match_team.csv')).drop(columns=['key']),
        'clasico_shots': pd.read_csv(os.path.join(PROCESSED, 'shots.csv')),
        'clasico_losses': pd.read_csv(os.path.join(PROCESSED, 'loss_table.csv')),
    }
    for name, df in out.items():
        df.to_csv(os.path.join(OUT, name + '.csv'), index=False, lineterminator='\n')
        log.info('wrote table', extra={'table': name, 'rows': len(df), 'columns': df.shape[1]})
    return out


if __name__ == '__main__':
    main()
