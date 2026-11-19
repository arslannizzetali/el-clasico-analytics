"""League-wide tables from the PostgreSQL event store (run scripts/load_db.py first).

    python3 analysis/league.py

Writes data/league/:
  match_team_<category>.csv   one row per team per match, every metric in clasico/frames.py
  by_period.csv               Barcelona and its opponents per category and period
  opponent_formations.csv     how teams lined up against Barcelona: top-10 clubs vs the rest
  real_madrid_2015_16.csv     Real Madrid's 2015/16 league season, Benítez vs Zidane

Rates are pooled (sum of the numerator over sum of the denominator), so a match with many pressures weighs
more than one with few; tempo metrics are averages of match values.
"""
import os
import sys

import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from clasico import ROOT, db, frames  # noqa: E402

OUT = os.path.join(ROOT, 'data', 'league')
CATEGORIES = ('clasico', 'barcelona_vs_top10', 'barcelona_all', 'season_2015_16')


def era(season):
    y = int(season[:4])
    return '2004-09' if y < 2009 else '2009-13' if y < 2013 else '2013-17' if y < 2017 else '2017-21'


def pooled(g):
    return pd.Series({
        'matches': g['match_id'].nunique(),
        'passes_per_shot': round(g['passes_before_shot_sum'].sum() / g['open_play_shots'].sum(), 1),
        'press_success_pct': round(100 * g['pressures_won_5s'].sum() / g['pressures'].sum(), 1),
        'ppda': round(g['opp_buildup_passes'].sum() / g['def_actions'].sum(), 1),
        'possession_pct': round(g['possession_pct'].mean(), 1),
        'pass_interval_s': round(g['pass_interval_s'].mean(), 2),
        'attack_speed_mps': round(g['attack_speed_mps'].mean(), 2),
        'np_xg_per_match': round(g['np_xg'].sum() / g['match_id'].nunique(), 2),
    })


def back_line(f):
    """Defenders in a formation string such as 5-3-2 or 3-4-3 (first number)."""
    return int(f.split('-')[0]) if f else None


def main():
    eng = db.engine()
    os.makedirs(OUT, exist_ok=True)
    top = set(pd.read_sql('SELECT team_name FROM top_clubs', eng)['team_name'])
    mt = {}
    for cat in CATEGORIES:
        ev, ms = frames.load(cat, eng)
        d = frames.match_team(ev, ms)
        d['period'] = d['season_name'].map(era)
        d.to_csv(os.path.join(OUT, f'match_team_{cat}.csv'), index=False)
        mt[cat] = d
        print(f'{cat}: {d["match_id"].nunique()} matches')

    rows = []
    for cat in ('clasico', 'barcelona_vs_top10', 'barcelona_all'):
        d = mt[cat]
        d = d.assign(side=d['team'].where(d['team'] == 'Barcelona', 'Opponent'))
        for (side, period), g in d.groupby(['side', 'period']):
            rows.append({'category': cat, 'side': side, 'period': period, **pooled(g)})
    pd.DataFrame(rows).astype({'matches': int}).to_csv(os.path.join(OUT, 'by_period.csv'), index=False)

    d = mt['barcelona_all']
    opp = d[d['team'] != 'Barcelona'].copy()
    opp['opponent_group'] = opp['team'].map(lambda t: 'Top-10 club' if t in top else 'Other club')
    opp['back_line'] = opp['formation'].map(back_line)
    f = opp.groupby(['opponent_group', 'period']).apply(lambda g: pd.Series({
        'matches': len(g),
        'most_common': g['formation'].mode().iat[0],
        'back_three_or_five_pct': round(100 * g['back_line'].isin([3, 5]).mean(), 1),
        'possession_pct': round(g['possession_pct'].mean(), 1),
        'formation_changes_per_match': round(g['formation_changes'].mean(), 2),
        'goals_against_barcelona': round(g['goals_for'].mean(), 2),
    }), include_groups=False).reset_index()
    f.to_csv(os.path.join(OUT, 'opponent_formations.csv'), index=False)

    rm = mt['season_2015_16']
    rm = rm[rm['team'] == 'Real Madrid'].copy()
    rm['coach_group'] = rm['coach'].where(rm['coach'].isin(['Zinédine Zidane', 'Rafael Benítez']), rm['coach'])
    s = rm.groupby('coach_group').apply(lambda g: pd.Series({
        **pooled(g),
        'points_per_match': round((3 * (g['goals_for'] > g['goals_against']).sum()
                                   + (g['goals_for'] == g['goals_against']).sum()) / len(g), 2),
        'most_common_formation': g['formation'].mode().iat[0],
    }), include_groups=False).reset_index().astype({'matches': int})
    s.to_csv(os.path.join(OUT, 'real_madrid_2015_16.csv'), index=False)

    with pd.option_context('display.width', 200, 'display.max_columns', 20):
        print(pd.read_csv(os.path.join(OUT, 'by_period.csv')).to_string(index=False))
        print(f.to_string(index=False))
        print(s.to_string(index=False))


if __name__ == '__main__':
    main()
