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
from clasico import OPP, PROCESSED, data  # noqa: E402
from clasico.output import write_json  # noqa: E402
from clasico.events import is_clean_receipt, passes_before, possessions, sec, strip_after  # noqa: E402

OUT = sys.argv[1] if len(sys.argv) > 1 else PROCESSED

# Two matches whose manager field is empty in the open data
COACH_FIX = {('2012-10-07', 'Barcelona'): 'Tito Vilanova', ('2013-03-02', 'Barcelona'): 'Tito Vilanova',
             ('2012-10-07', 'Real Madrid'): 'José Mourinho', ('2013-03-02', 'Real Madrid'): 'José Mourinho'}
START = {'Regular Play': 'Open play', 'From Counter': 'Counter', 'From Free Kick': 'Free kick', 'From Corner': 'Corner',
         'From Throw In': 'Throw-in', 'From Goal Kick': 'Goal kick', 'From Keeper': 'From keeper', 'From Kick Off': 'Kick-off'}
OUTCOME = {'Goal': 'Goal', 'Saved': 'Saved', 'Off T': 'Off target', 'Blocked': 'Blocked', 'Post': 'Post', 'Wayward': 'Wayward',
           'Saved Off Target': 'Saved', 'Saved to Post': 'Saved (post)'}
SET_PIECES = ('From Corner', 'From Free Kick')


def era(season):
    y = int(season[:4])
    return '2005-09' if y < 2009 else '2009-13' if y < 2013 else '2013-17' if y < 2017 else '2017-21'


def manager(team):
    m = team.get('managers') or []
    return m[0].get('nickname') or m[0]['name'] if m else ''


def match_rows(g, ev, shots_out):
    """Metric rows for both teams in one match; appends the shots to shots_out."""
    mid = g['match_id']
    h, a = g['home_team']['home_team_name'], g['away_team']['away_team_name']
    form = {e['team']['name']: str(e['tactics']['formation']) for e in ev if e['type']['name'] == 'Starting XI'}
    coach = {h: manager(g['home_team']), a: manager(g['away_team'])}
    goals = {h: g['home_score'], a: g['away_score']}
    label = f"{g['match_date']}  {h} {g['home_score']}-{g['away_score']} {a}"
    row = {t: dict(match_id=mid, date=g['match_date'], season=g['season'], match=label, team=t, opponent=OPP[t],
                   venue='Home' if t == h else 'Away', goals_for=goals[t], goals_against=goals[OPP[t]],
                   formation='-'.join(form[t]), coach=coach[t]) for t in OPP}

    seqs = possessions(ev)
    A = collections.defaultdict(lambda: collections.defaultdict(list))
    for i, q in enumerate(seqs):
        es = q['es']
        # Passes before shot: every shot is listed, but the metric uses only the first shot of a possession
        # (so a rebound does not count the same possession's passes twice).
        sh = [e for e in es if e['type']['name'] == 'Shot' and e['shot']['type']['name'] != 'Penalty']
        op = q['pp'] not in SET_PIECES
        for k, s0 in enumerate(sh):
            t = s0['team']['name']
            n = passes_before(es, s0)
            dur = round(sec(s0) - sec(es[0]), 1)
            if op and k == 0:
                A[t]['np'].append(n)
            shots_out.append(dict(match_id=mid, match=label, date=g['match_date'], minute=s0['minute'], team=t,
                                  player=s0['player']['name'], passes_before=n, seconds=dur, start=q['pp'], open_play=op,
                                  outcome=s0['shot']['outcome']['name'], xg=round(s0['shot']['statsbomb_xg'], 2),
                                  x=round(s0['location'][0], 1), y=round(s0['location'][1], 1), first_in_attack=1 if k == 0 else 0))
        # Turnover: the ball passing to the opponent in open play. Opponent shot within 15 s, regain within 8 s.
        if i > 0 and seqs[i - 1]['team'] != q['team'] and seqs[i - 1]['per'] == q['per'] and q['pp'] in ('Regular Play', 'From Counter'):
            W = q['team']
            L = OPP[W]
            if next((e for e in es if 'location' in e and e['team']['name'] == W), None):
                t0 = sec(es[0])
                after = [e for e in ev if e['period'] == q['per'] and t0 <= sec(e) <= t0 + 15 and e['index'] >= es[0]['index']]
                A[L]['loss'].append(1)
                A[L]['reg'].append(any(e['possession_team']['name'] == L and e['possession'] != q['p'] and sec(e) <= t0 + 8 for e in after))
                A[L]['shot15'].append(any(e['type']['name'] == 'Shot' and e['team']['name'] == W for e in after))

    # Ball strip: the opponent controls the ball and loses it before releasing it. Credited to the pressing team.
    CT = collections.defaultdict(collections.Counter)
    for i, e in enumerate(ev):
        if not is_clean_receipt(e):
            continue
        c = CT[OPP[e['team']['name']]]
        c['ctrl'] += 1
        if strip_after(ev, i) is not None:
            c['lost'] += 1
            x0 = e['location'][0]
            c['z_att' if x0 < 40 else 'z_mid' if x0 < 80 else 'z_def'] += 1

    ts = [(e['period'], sec(e), e['possession_team']['name']) for e in ev]
    out = []
    for T in OPP:
        r, Opp = row[T], OPP[T]
        pr = [e for e in ev if e['type']['name'] == 'Pressure' and e['team']['name'] == T]
        opass = [e for e in ev if e['type']['name'] == 'Pass' and e['team']['name'] == Opp]
        da = [e for e in ev if e['team']['name'] == T and 'location' in e and e['location'][0] >= 48 and (
            e['type']['name'] in ('Interception', 'Foul Committed') or (e['type']['name'] == 'Duel' and e['duel']['type']['name'] == 'Tackle'))]
        ok = sum(1 for e in pr if any(p == e['period'] and sec(e) < tt <= sec(e) + 5 and pt == T for p, tt, pt in ts))
        buildup = sum(1 for e in opass if e['location'][0] <= 72)
        np_ = A[T]['np']
        r.update(passes=sum(1 for e in ev if e['type']['name'] == 'Pass' and e['team']['name'] == T),
                 open_play_shots=len(np_), passes_before_shot_sum=sum(np_),
                 passes_per_shot=round(st.mean(np_), 1) if np_ else None,
                 direct_shots=sum(v <= 2 for v in np_), long_shots=sum(v >= 8 for v in np_),
                 turnovers=len(A[T]['loss']), conceded_shot_15s=sum(A[T]['shot15']), regained_8s=sum(A[T]['reg']),
                 pressures=len(pr), opp_passes=len(opass), pressures_won_5s=ok,
                 press_success_pct=round(100 * ok / len(pr), 1),
                 opp_buildup_passes=buildup, def_actions=len(da),
                 ppda=round(buildup / max(1, len(da)), 1),
                 opp_controls=CT[T]['ctrl'], balls_stripped=CT[T]['lost'], stripped_per100=round(100 * CT[T]['lost'] / CT[T]['ctrl'], 1),
                 stripped_att_third=CT[T]['z_att'], stripped_mid_third=CT[T]['z_mid'], stripped_def_third=CT[T]['z_def'])
        out.append(r)
    return out


def main():
    M, S = [], []
    for g in data.clasico_matches():
        M.extend(match_rows(g, data.events(g['match_id']), S))
    per = {m['match_id']: era(m['season']) for m in M}
    for m in M:
        m['period'] = per[m['match_id']]
        if not m['coach']:
            m['coach'] = COACH_FIX[(m['date'], m['team'])]
        m['conceded_shot_15s_pct'] = round(100 * m['conceded_shot_15s'] / m['turnovers'], 1)
        m['regained_8s_pct'] = round(100 * m['regained_8s'] / m['turnovers'], 1)
        m['key'] = f"{m['match_id']}|{m['team']}"
    S.sort(key=lambda r: (r['date'], r['minute']))
    for i, r in enumerate(S):
        r['shot_id'] = i + 1
        r['period'] = per[r['match_id']]
        r['start'] = START[r['start']]
        r['outcome'] = OUTCOME.get(r['outcome'], r['outcome'])
        r['open_play'] = 1 if r['open_play'] else 0
    os.makedirs(OUT, exist_ok=True)
    for name, rows in (('match_team', M), ('shots', S)):
        with open(os.path.join(OUT, name + '.csv'), 'w', newline='') as fh:
            w = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
            w.writeheader()
            w.writerows(rows)
        write_json(os.path.join(OUT, name + '.json'), rows)
    print(f'build: {len(M)} match-team rows, {len(S)} shots')


if __name__ == '__main__':
    main()
