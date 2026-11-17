"""Step 4: the main metrics split by game state (game_state.json).

Every event is labelled Ahead / Level / Behind for each team from the goals scored before it. Goals: every
shot with outcome Goal (penalties included) and "Own Goal For" events. Metrics use the same definitions as
build.py, but numerators and denominators are summed per state; the three states add up to build.py's match
totals (checked at the end). Minutes spent in each state are written too.
Input: match_team.json (build.py).
"""
import collections
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from clasico import OPP, PROCESSED, data  # noqa: E402
from clasico.events import (STATES, game_state, is_clean_receipt, passes_before, possessions,  # noqa: E402
                            score_before, sec, strip_after)
from clasico.output import read_json, write_rows  # noqa: E402

OUT = sys.argv[1] if len(sys.argv) > 1 else PROCESSED
FIELDS = ('open_play_shots', 'passes_before_shot_sum', 'pressures', 'pressures_won_5s', 'opp_buildup_passes',
          'def_actions', 'opp_controls', 'balls_stripped')


def match_states(ev, final):
    """{(team, state): Counter} with metric numerators/denominators and 'seconds'."""
    ev = sorted(ev, key=lambda e: e['index'])
    before, score = score_before(ev, OPP)
    for t in OPP:
        assert score[t] == final[t], ('score mismatch', t, score, final)

    def state(i, t):
        return game_state(before[i], t, OPP[t])

    pos = {e['id']: i for i, e in enumerate(ev)}
    acc = {(t, s): collections.Counter() for t in OPP for s in STATES}
    # Minutes: timestamps do not always increase in event order, so within each half events are sorted by
    # time and the gap between two consecutive events is credited to the first event's state.
    for per in (1, 2):
        idx = sorted((i for i, e in enumerate(ev) if e['period'] == per), key=lambda i: (sec(ev[i]), ev[i]['index']))
        for a, b in zip(idx, idx[1:]):
            for t in OPP:
                acc[(t, state(a, t))]['seconds'] += sec(ev[b]) - sec(ev[a])
    # Passes before shot (first shot of the possession, set pieces excluded)
    for q in possessions(ev):
        shots = [e for e in q['es'] if e['type']['name'] == 'Shot' and e['shot']['type']['name'] != 'Penalty']
        if shots and q['pp'] not in ('From Corner', 'From Free Kick'):
            t = shots[0]['team']['name']
            counts = acc[(t, state(pos[shots[0]['id']], t))]
            counts['open_play_shots'] += 1
            counts['passes_before_shot_sum'] += passes_before(q['es'], shots[0])
    # Press success and PPDA
    ts = [(e['period'], sec(e), e['possession_team']['name']) for e in ev]
    for i, e in enumerate(ev):
        name, t = e['type']['name'], e['team']['name']
        if name == 'Pressure':
            counts = acc[(t, state(i, t))]
            counts['pressures'] += 1
            if any(p == e['period'] and sec(e) < tt <= sec(e) + 5 and pt == t for p, tt, pt in ts):
                counts['pressures_won_5s'] += 1
        if name == 'Pass' and e['location'][0] <= 72:
            acc[(OPP[t], state(i, OPP[t]))]['opp_buildup_passes'] += 1
        is_def_action = name in ('Interception', 'Foul Committed') or (
            name == 'Duel' and e['duel']['type']['name'] == 'Tackle')
        if 'location' in e and e['location'][0] >= 48 and is_def_action:
            acc[(t, state(i, t))]['def_actions'] += 1
    # Ball strips: state from the pressing team's view, at the moment of the receipt
    for i, e in enumerate(ev):
        if not is_clean_receipt(e):
            continue
        defending = OPP[e['team']['name']]
        counts = acc[(defending, state(i, defending))]
        counts['opp_controls'] += 1
        if strip_after(ev, i) is not None:
            counts['balls_stripped'] += 1
    return acc


def main():
    match_team = read_json(os.path.join(OUT, 'match_team.json'))
    rows = []
    for mid in sorted({m['match_id'] for m in match_team}):
        meta = {m['team']: m for m in match_team if m['match_id'] == mid}
        by_state = match_states(data.events(mid), {t: meta[t]['goals_for'] for t in OPP})
        for (t, s), counts in by_state.items():
            m = meta[t]
            rows.append(dict(key=f'{mid}|{t}|{s}', match_id=mid, match=m['match'], date=m['date'], period=m['period'],
                             coach=m['coach'], team=t, state=s, minutes=round(counts['seconds'] / 60, 1),
                             **{k: counts[k] for k in FIELDS}))
    # Check: the three states add up to build.py's match totals
    tot = collections.defaultdict(collections.Counter)
    for r in rows:
        for f in FIELDS:
            tot[(r['match_id'], r['team'])][f] += r[f]
    bad = [(m['match_id'], m['team'], f) for m in match_team for f in FIELDS
           if tot[(m['match_id'], m['team'])][f] != m[f]]
    assert not bad, bad[:5]
    write_rows(os.path.join(OUT, 'game_state.json'), rows, os.path.abspath(__file__))
    print(f'game_state: {len(rows)} rows; states add up to match totals')


if __name__ == '__main__':
    main()
