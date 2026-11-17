"""Step 1: match-team metrics (match_team) and the shot list (shots).

Input: StatsBomb open data (downloaded to data/raw if missing).
Output: match_team.json/.csv (one row per team per match), shots.json/.csv (every non-penalty shot).
"""
import collections
import csv
import os
import statistics as st
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from clasico import BARCELONA_COACHES, OPP, PROCESSED, data  # noqa: E402
from clasico.output import write_json  # noqa: E402
from clasico.events import is_clean_receipt, passes_before, possessions, sec, strip_after  # noqa: E402

OUT = sys.argv[1] if len(sys.argv) > 1 else PROCESSED

# Two matches whose manager field is empty in the open data
COACH_FIX = {
    ('2012-10-07', 'Barcelona'): 'Tito Vilanova',
    ('2013-03-02', 'Barcelona'): 'Tito Vilanova',
    ('2012-10-07', 'Real Madrid'): 'José Mourinho',
    ('2013-03-02', 'Real Madrid'): 'José Mourinho',
}
START = {
    'Regular Play': 'Open play', 'From Counter': 'Counter', 'From Free Kick': 'Free kick',
    'From Corner': 'Corner', 'From Throw In': 'Throw-in', 'From Goal Kick': 'Goal kick',
    'From Keeper': 'From keeper', 'From Kick Off': 'Kick-off',
}
OUTCOME = {
    'Goal': 'Goal', 'Saved': 'Saved', 'Off T': 'Off target', 'Blocked': 'Blocked', 'Post': 'Post',
    'Wayward': 'Wayward', 'Saved Off Target': 'Saved', 'Saved to Post': 'Saved (post)',
}
SET_PIECES = ('From Corner', 'From Free Kick')
OPEN_PLAY_STARTS = ('Regular Play', 'From Counter')
QUICK_SHOT_WINDOW = 15   # seconds after a turnover in which an opponent shot counts
REGAIN_WINDOW = 8        # seconds after a turnover in which winning the ball back counts
PRESS_WIN_WINDOW = 5     # seconds after a pressure in which the pressing team must have the ball
BUILDUP_MAX_X = 72       # opponent passes at or behind this x are build-up passes (PPDA numerator)
DEF_ACTION_MIN_X = 48    # defensive actions at or beyond this x count (PPDA denominator)


def era(season):
    year = int(season[:4])
    if year < 2009:
        return '2005-09'
    if year < 2013:
        return '2009-13'
    if year < 2017:
        return '2013-17'
    return '2017-21'


def manager(team):
    managers = team.get('managers') or []
    return managers[0].get('nickname') or managers[0]['name'] if managers else ''


def is_open_play_shot_event(e):
    return e['type']['name'] == 'Shot' and e['shot']['type']['name'] != 'Penalty'


def base_rows(match, ev):
    """The identifying fields of both team rows, keyed by team."""
    home = match['home_team']['home_team_name']
    away = match['away_team']['away_team_name']
    formation = {e['team']['name']: str(e['tactics']['formation']) for e in ev if e['type']['name'] == 'Starting XI'}
    coach = {home: manager(match['home_team']), away: manager(match['away_team'])}
    goals = {home: match['home_score'], away: match['away_score']}
    label = f"{match['match_date']}  {home} {match['home_score']}-{match['away_score']} {away}"
    rows = {}
    for team in OPP:
        rows[team] = dict(
            match_id=match['match_id'], date=match['match_date'], season=match['season'], match=label,
            team=team, opponent=OPP[team], venue='Home' if team == home else 'Away',
            goals_for=goals[team], goals_against=goals[OPP[team]],
            formation='-'.join(formation[team]), coach=coach[team])
    return rows, label


def shot_metrics(match, label, seqs, shots_out):
    """Passes before each open-play shot, per team; appends every non-penalty shot to shots_out.

    Every shot is listed, but the metric uses only the first shot of a possession
    (so a rebound does not count the same possession's passes twice)."""
    passes_per_shot = collections.defaultdict(list)
    for seq in seqs:
        events = seq['es']
        shots = [e for e in events if is_open_play_shot_event(e)]
        open_play = seq['pp'] not in SET_PIECES
        for k, shot in enumerate(shots):
            team = shot['team']['name']
            n_passes = passes_before(events, shot)
            duration = round(sec(shot) - sec(events[0]), 1)
            if open_play and k == 0:
                passes_per_shot[team].append(n_passes)
            shots_out.append(dict(
                match_id=match['match_id'], match=label, date=match['match_date'], minute=shot['minute'],
                team=team, player=shot['player']['name'], passes_before=n_passes, seconds=duration,
                start=seq['pp'], open_play=open_play, outcome=shot['shot']['outcome']['name'],
                xg=round(shot['shot']['statsbomb_xg'], 2),
                x=round(shot['location'][0], 1), y=round(shot['location'][1], 1),
                first_in_attack=1 if k == 0 else 0))
    return passes_per_shot


def turnover_metrics(ev, seqs):
    """Turnover: the ball passing to the opponent in open play. For the team that lost it:
    one entry per turnover, whether it won the ball back within 8 s, whether the opponent shot within 15 s."""
    turnovers = collections.defaultdict(lambda: collections.defaultdict(list))
    for i, seq in enumerate(seqs):
        if i == 0:
            continue
        previous = seqs[i - 1]
        if previous['team'] == seq['team'] or previous['per'] != seq['per'] or seq['pp'] not in OPEN_PLAY_STARTS:
            continue
        events = seq['es']
        winner = seq['team']
        loser = OPP[winner]
        if not any('location' in e and e['team']['name'] == winner for e in events):
            continue
        t0 = sec(events[0])
        after = [e for e in ev if e['period'] == seq['per'] and t0 <= sec(e) <= t0 + QUICK_SHOT_WINDOW
                 and e['index'] >= events[0]['index']]
        lost = turnovers[loser]
        lost['loss'].append(1)
        lost['reg'].append(any(e['possession_team']['name'] == loser and e['possession'] != seq['p']
                               and sec(e) <= t0 + REGAIN_WINDOW for e in after))
        lost['shot15'].append(any(e['type']['name'] == 'Shot' and e['team']['name'] == winner for e in after))
    return turnovers


def strip_metrics(ev):
    """Ball strip: the opponent controls the ball and loses it before releasing it. Credited to the pressing team."""
    strips = collections.defaultdict(collections.Counter)
    for i, e in enumerate(ev):
        if not is_clean_receipt(e):
            continue
        counts = strips[OPP[e['team']['name']]]
        counts['ctrl'] += 1
        if strip_after(ev, i) is not None:
            counts['lost'] += 1
            x0 = e['location'][0]
            counts['z_att' if x0 < 40 else 'z_mid' if x0 < 80 else 'z_def'] += 1
    return strips


def is_defensive_action(e):
    name = e['type']['name']
    return name in ('Interception', 'Foul Committed') or (name == 'Duel' and e['duel']['type']['name'] == 'Tackle')


def press_metrics(ev, team, possession_times):
    """Pressures, press success within 5 s and PPDA for one team."""
    opponent = OPP[team]
    pressures = [e for e in ev if e['type']['name'] == 'Pressure' and e['team']['name'] == team]
    opp_passes = [e for e in ev if e['type']['name'] == 'Pass' and e['team']['name'] == opponent]
    def_actions = [e for e in ev if e['team']['name'] == team and 'location' in e
                   and e['location'][0] >= DEF_ACTION_MIN_X and is_defensive_action(e)]
    won = sum(1 for e in pressures
              if any(period == e['period'] and sec(e) < t <= sec(e) + PRESS_WIN_WINDOW and owner == team
                     for period, t, owner in possession_times))
    buildup = sum(1 for e in opp_passes if e['location'][0] <= BUILDUP_MAX_X)
    return dict(
        pressures=len(pressures), opp_passes=len(opp_passes), pressures_won_5s=won,
        press_success_pct=round(100 * won / len(pressures), 1),
        opp_buildup_passes=buildup, def_actions=len(def_actions),
        ppda=round(buildup / max(1, len(def_actions)), 1))


def match_rows(match, ev, shots_out):
    """Metric rows for both teams in one match; appends the shots to shots_out."""
    rows, label = base_rows(match, ev)
    seqs = possessions(ev)
    passes_per_shot = shot_metrics(match, label, seqs, shots_out)
    turnovers = turnover_metrics(ev, seqs)
    strips = strip_metrics(ev)
    possession_times = [(e['period'], sec(e), e['possession_team']['name']) for e in ev]
    out = []
    for team in OPP:
        row = rows[team]
        shot_passes = passes_per_shot[team]
        lost = turnovers[team]
        stripped = strips[team]
        press = press_metrics(ev, team, possession_times)
        row.update(
            passes=sum(1 for e in ev if e['type']['name'] == 'Pass' and e['team']['name'] == team),
            open_play_shots=len(shot_passes), passes_before_shot_sum=sum(shot_passes),
            passes_per_shot=round(st.mean(shot_passes), 1) if shot_passes else None,
            direct_shots=sum(v <= 2 for v in shot_passes), long_shots=sum(v >= 8 for v in shot_passes),
            turnovers=len(lost['loss']), conceded_shot_15s=sum(lost['shot15']), regained_8s=sum(lost['reg']),
            **press,
            opp_controls=stripped['ctrl'], balls_stripped=stripped['lost'],
            stripped_per100=round(100 * stripped['lost'] / stripped['ctrl'], 1),
            stripped_att_third=stripped['z_att'], stripped_mid_third=stripped['z_mid'],
            stripped_def_third=stripped['z_def'])
        out.append(row)
    return out


def finish_match_rows(match_team, period_of):
    for row in match_team:
        row['period'] = period_of[row['match_id']]
        if not row['coach']:
            row['coach'] = COACH_FIX[(row['date'], row['team'])]
    barcelona_coach = {row['match_id']: row['coach'] for row in match_team if row['team'] == 'Barcelona'}
    for row in match_team:
        # Both teams' rows of a match carry Barcelona's coach, so either team can be grouped by it
        row['coach_group'] = BARCELONA_COACHES[barcelona_coach[row['match_id']]]
        row['conceded_shot_15s_pct'] = round(100 * row['conceded_shot_15s'] / row['turnovers'], 1)
        row['regained_8s_pct'] = round(100 * row['regained_8s'] / row['turnovers'], 1)
        row['key'] = f"{row['match_id']}|{row['team']}"


def finish_shots(shots, period_of):
    shots.sort(key=lambda r: (r['date'], r['minute']))
    for i, shot in enumerate(shots):
        shot['shot_id'] = i + 1
        shot['period'] = period_of[shot['match_id']]
        shot['start'] = START[shot['start']]
        shot['outcome'] = OUTCOME.get(shot['outcome'], shot['outcome'])
        shot['open_play'] = 1 if shot['open_play'] else 0


def write_table(name, rows):
    with open(os.path.join(OUT, name + '.csv'), 'w', newline='') as fh:
        writer = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)
    write_json(os.path.join(OUT, name + '.json'), rows)


def main():
    match_team, shots = [], []
    for match in data.clasico_matches():
        match_team.extend(match_rows(match, data.events(match['match_id']), shots))
    period_of = {row['match_id']: era(row['season']) for row in match_team}
    finish_match_rows(match_team, period_of)
    finish_shots(shots, period_of)
    os.makedirs(OUT, exist_ok=True)
    write_table('match_team', match_team)
    write_table('shots', shots)
    print(f'build: {len(match_team)} match-team rows, {len(shots)} shots')


if __name__ == '__main__':
    main()
