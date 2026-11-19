"""Match-team metrics with pandas, on events read from PostgreSQL.

The definitions are the reference pipeline's (scripts/build.py, clasico/events.py), written as vectorised
DataFrame operations so they run on any set of matches, not only the Clásicos. tests/test_frames.py checks
that both give the same numbers on the Clásicos.

    from clasico import db, frames
    ev, ms = frames.load('barcelona_vs_top10', db.engine())
    mt = frames.match_team(ev, ms)
"""
import numpy as np
import pandas as pd

SET_PIECES = ('From Corner', 'From Free Kick')
OPEN_PLAY = ('Regular Play', 'From Counter')
PRESS_WINDOW = 5        # seconds: a pressure succeeds if its team has the ball within this
PPDA_BUILDUP_X = 72     # opponent passes at x <= 72 are build-up passes
PPDA_DEFENCE_X = 48     # defensive actions at x >= 48 count
METRES_PER_UNIT = 105 / 120   # StatsBomb pitch is 120 units long; a typical pitch is 105 m
MIN_ATTACK_SECONDS = 3  # possessions shorter than this are left out of the speed metrics

EVENTS_SQL = """
SELECT e.match_id, e.idx, e.period, e.minute, e.ts, e.type, t.team_name AS team, e.player_id,
       e.possession, pt.team_name AS possession_team, e.play_pattern,
       e.x, e.y, e.end_x, e.end_y, e.outcome, e.subtype, e.xg
FROM events e
JOIN teams t  ON t.team_id = e.team_id
JOIN teams pt ON pt.team_id = e.possession_team_id
WHERE e.period <= 2 AND e.match_id IN (SELECT match_id FROM match_categories WHERE category = %(category)s)
ORDER BY e.match_id, e.idx
"""

MATCHES_SQL = """
SELECT l.*, f_h.formation AS home_formation, f_a.formation AS away_formation
FROM match_list l
JOIN matches m USING (match_id)
LEFT JOIN formations f_h ON f_h.match_id = l.match_id AND f_h.team_id = m.home_team_id AND f_h.starting
LEFT JOIN formations f_a ON f_a.match_id = l.match_id AND f_a.team_id = m.away_team_id AND f_a.starting
WHERE l.match_id IN (SELECT match_id FROM match_categories WHERE category = %(category)s)
ORDER BY l.match_date, l.match_id
"""


def load(category, engine):
    """Events (periods 1-2) and matches of one category, as two DataFrames."""
    p = {'category': category}
    return pd.read_sql(EVENTS_SQL, engine, params=p), pd.read_sql(MATCHES_SQL, engine, params=p)


def team_rows(ms):
    """Two rows per match: team, opponent, venue, goals, coach and starting formation."""
    side = []
    for home in (True, False):
        a, b = ('home', 'away') if home else ('away', 'home')
        d = ms[['match_id', 'season_name', 'match_date']].copy()
        d['team'], d['opponent'] = ms[a], ms[b]
        d['venue'] = 'Home' if home else 'Away'
        d['goals_for'], d['goals_against'] = ms[f'{a}_score'], ms[f'{b}_score']
        d['coach'] = ms[f'{a}_manager']
        d['formation'] = ms[f'{a}_formation'].fillna('').map(lambda f: '-'.join(f))
        side.append(d)
    return pd.concat(side).sort_values(['match_date', 'match_id', 'venue'], ascending=[True, True, False]).reset_index(drop=True)


def add_sequences(ev):
    """StatsBomb possessions as the reference pipeline groups them: a new sequence whenever the period or
    possession number changes in event order. Adds seq, seq_team (team in possession), seq_pattern,
    seq_start/seq_end (seconds) to ev."""
    ev = ev.sort_values(['match_id', 'idx']).reset_index(drop=True)
    key = ev[['match_id', 'period', 'possession']]
    ev['seq'] = (key != key.shift()).any(axis=1).cumsum()
    g = ev.groupby('seq')
    ev['seq_team'] = g['possession_team'].transform('first')
    ev['seq_pattern'] = g['play_pattern'].transform('first')
    ev['seq_start'] = g['ts'].transform('first')
    ev['seq_end'] = g['ts'].transform('last')
    return ev


def build_up(ev):
    """Passes before a team's first non-penalty shot of each open-play possession (corners and free kicks
    excluded). Later shots in the same possession are not counted, so passes are not double-counted."""
    completed = (ev['type'] == 'Pass') & ev['outcome'].isna()
    # completed passes by each team so far in the sequence; a shot row is not a pass, so this counts the passes before it
    passes_so_far = completed.astype(int).groupby([ev['seq'], ev['team']]).cumsum()
    shots = ev[(ev['type'] == 'Shot') & (ev['subtype'] != 'Penalty')].assign(passes_before=passes_so_far)
    first = shots.drop_duplicates('seq')
    first = first[~first['seq_pattern'].isin(SET_PIECES)]
    out = first.groupby(['match_id', 'team'])['passes_before'].agg(
        open_play_shots='size', passes_before_shot_sum='sum',
        direct_shots=lambda s: int((s <= 2).sum()), long_shots=lambda s: int((s >= 8).sum()))
    out['passes_per_shot'] = (out['passes_before_shot_sum'] / out['open_play_shots']).round(1)
    return out


def pressing(ev, tr):
    """Pressures, press success (own possession within 5 s) and PPDA per match-team.
    tr: team_rows(), for the opponent of each team."""
    opp = tr.set_index(['match_id', 'team'])['opponent']
    pr = ev[ev['type'] == 'Pressure']
    won = pd.Series(False, index=pr.index)
    # For each (match, period): sorted event times and, per team, how many events with that team in possession
    # come up to each time, so "any own-possession event in (t, t + 5]" is a difference of two counts.
    for (mid, per), e in ev.groupby(['match_id', 'period']):
        ts = e['ts'].to_numpy()
        order = np.argsort(ts, kind='stable')
        ts_sorted = ts[order]
        p = pr[(pr['match_id'] == mid) & (pr['period'] == per)]
        lo = np.searchsorted(ts_sorted, p['ts'].to_numpy(), side='right')
        hi = np.searchsorted(ts_sorted, p['ts'].to_numpy() + PRESS_WINDOW, side='right')
        for team in p['team'].unique():
            own = np.concatenate([[0], np.cumsum(e['possession_team'].to_numpy()[order] == team)])
            m = (p['team'] == team).to_numpy()
            won.loc[p.index[m]] = (own[hi[m]] - own[lo[m]]) > 0
    passes = ev[ev['type'] == 'Pass']
    da = ev[(ev['x'] >= PPDA_DEFENCE_X) & (ev['type'].isin(['Interception', 'Foul Committed'])
                                          | ((ev['type'] == 'Duel') & (ev['subtype'] == 'Tackle')))]
    idx = pd.MultiIndex.from_frame(tr[['match_id', 'team']])
    out = pd.DataFrame(index=idx)
    out['passes'] = passes.groupby(['match_id', 'team']).size()
    out['pressures'] = pr.groupby(['match_id', 'team']).size()
    out['pressures_won_5s'] = won.groupby([pr['match_id'], pr['team']]).sum()
    out['def_actions'] = da.groupby(['match_id', 'team']).size()
    buildup = passes[passes['x'] <= PPDA_BUILDUP_X].groupby(['match_id', 'team']).size()
    out['opp_passes'] = [out['passes'].get((m, opp[(m, t)]), 0) for m, t in out.index]
    out['opp_buildup_passes'] = [buildup.get((m, opp[(m, t)]), 0) for m, t in out.index]
    out = out.fillna(0).astype(int)
    out['press_success_pct'] = (100 * out['pressures_won_5s'] / out['pressures']).round(1)
    out['ppda'] = (out['opp_buildup_passes'] / out['def_actions'].clip(lower=1)).round(1)
    return out


def tempo(ev):
    """How fast a team plays when it has the ball (new metrics, not in the reference pipeline).

    possession_pct      share of the match's possession time (first to last event of each possession)
    pass_interval_s     median seconds between two consecutive passes of the team in the same open-play possession
    attack_speed_mps    forward metres per second in open-play possessions of 3 s or more: from where the
                        possession starts to the furthest point the ball reaches (pass/carry end), over its length
    """
    seqs = ev.groupby('seq').agg(match_id=('match_id', 'first'), team=('seq_team', 'first'),
                                 pattern=('seq_pattern', 'first'), start=('seq_start', 'first'), end=('seq_end', 'first'))
    seqs['dur'] = seqs['end'] - seqs['start']
    share = seqs.groupby(['match_id', 'team'])['dur'].sum()
    possession_pct = (100 * share / share.groupby('match_id').transform('sum')).round(1)

    own = ev[(ev['team'] == ev['seq_team']) & ev['seq_pattern'].isin(OPEN_PLAY) & ev['x'].notna()]
    reach = own['end_x'].fillna(own['x'])
    g = own.assign(reach=reach).groupby('seq').agg(x0=('x', 'first'), reach=('reach', 'max'))
    s = seqs.join(g, how='inner')
    s = s[s['dur'] >= MIN_ATTACK_SECONDS]
    s['forward'] = ((s['reach'] - s['x0']).clip(lower=0)) * METRES_PER_UNIT
    sums = s.groupby(['match_id', 'team'])[['forward', 'dur']].sum()
    attack_speed = (sums['forward'] / sums['dur']).round(2)

    p = ev[(ev['type'] == 'Pass') & (ev['team'] == ev['seq_team']) & ev['seq_pattern'].isin(OPEN_PLAY)]
    gap = p.groupby('seq')['ts'].diff()
    pass_interval = gap.groupby([p['match_id'], p['team']]).median().round(2)

    return pd.DataFrame({'possession_pct': possession_pct, 'pass_interval_s': pass_interval,
                         'attack_speed_mps': attack_speed})


def shot_quality(ev):
    """Non-penalty xG for and shots, per match-team."""
    s = ev[(ev['type'] == 'Shot') & (ev['subtype'] != 'Penalty')]
    return s.groupby(['match_id', 'team']).agg(shots=('xg', 'size'), np_xg=('xg', 'sum')).round({'np_xg': 2})


def formation_changes(ev):
    return ev[ev['type'] == 'Tactical Shift'].groupby(['match_id', 'team']).size().rename('formation_changes')


def match_team(ev, ms):
    """One row per team per match with every metric above."""
    ev = add_sequences(ev)
    tr = team_rows(ms)
    parts = [build_up(ev), pressing(ev, tr), tempo(ev), shot_quality(ev), formation_changes(ev)]
    out = tr.set_index(['match_id', 'team']).join(parts, how='left')
    for c in ('open_play_shots', 'passes_before_shot_sum', 'direct_shots', 'long_shots', 'shots', 'formation_changes'):
        out[c] = out[c].fillna(0).astype(int)
    out['np_xg'] = out['np_xg'].fillna(0.0)
    return out.reset_index()
