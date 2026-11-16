"""Step 2: every ball lost after a controlled touch (losses_ds.json).

Loss: a player receives the ball and loses it before releasing it (clasico.events.strip_after).
Result: "Shot" if the opponent shoots within 20 seconds of the loss, "Goal" if they score.
Locations are from the losing team's view (attacking left to right). Input: match_team.json (build.py).
"""
import collections
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from clasico import OPP, PROCESSED, data  # noqa: E402
from clasico.events import LOSS_KIND, is_clean_receipt, sec, strip_after  # noqa: E402
from clasico.output import read_json, write_rows  # noqa: E402

OUT = sys.argv[1] if len(sys.argv) > 1 else PROCESSED
WINDOW = 20  # seconds: an opponent shot within this window counts as "ended in a shot"
NO_SHOT = dict(shot_x=None, shot_y=None, shot_xg=None, shot_event=None, shot_player=None, shot_minute=None)


def match_losses(mid, label, period, ev, start_id):
    shots = [e for e in ev if e['type']['name'] == 'Shot' and e['shot']['type']['name'] != 'Penalty']
    rows = []
    for i, e in enumerate(ev):
        if not is_clean_receipt(e):
            continue
        L = strip_after(ev, i)
        if L is None:
            continue
        TA = e['team']['name']
        t1 = sec(L)
        x, y = L['location'][:2]
        after = [s for s in shots if s['period'] == L['period'] and s['team']['name'] == OPP[TA] and t1 < sec(s) <= t1 + WINDOW]
        goal = any(s['shot']['outcome']['name'] == 'Goal' for s in after)
        # The shot shown on the map: the goal if there was one, otherwise the highest-xG shot. Its location is
        # turned to the losing team's view (the opponent attacks right to left: 120-x, 80-y).
        ch = max(after, key=lambda s: (s['shot']['outcome']['name'] == 'Goal', s['shot']['statsbomb_xg'])) if after else None
        sx = dict(shot_x=round(120 - ch['location'][0], 1), shot_y=round(80 - ch['location'][1], 1), shot_xg=round(ch['shot']['statsbomb_xg'], 2),
                  shot_event=ch['id'], shot_player=ch['player']['name'], shot_minute=ch['minute']) if ch else dict(NO_SHOT)
        r = dict(loss_id=start_id + len(rows), match_id=mid, match=label, period=period, minute=L['minute'], team=TA,
                 player=e['player']['name'], kind=LOSS_KIND[L['type']['name']],
                 x=round(x, 1), y=round(y, 1), third='own' if x < 40 else 'mid' if x < 80 else 'opp',
                 shot=1 if after else 0, goal=1 if goal else 0, xg=round(max((s['shot']['statsbomb_xg'] for s in after), default=0), 2),
                 result='Goal' if goal else 'Shot' if after else 'No shot')
        r.update(sx)
        rows.append(r)
    return rows


def main():
    M = read_json(os.path.join(OUT, 'match_team.json'))
    rows = []
    for mid, date, period, label in sorted({(m['match_id'], m['date'], m['period'], m['match']) for m in M}, key=lambda z: z[1]):
        rows += match_losses(mid, label, period, data.events(mid), len(rows) + 1)
    write_rows(os.path.join(OUT, 'losses_ds.json'), rows, os.path.abspath(__file__))
    A = collections.Counter()
    for r in rows:
        A[r['team'], 'n'] += 1
        A[r['team'], 'shot'] += r['shot']
        A[r['team'], 'goal'] += r['goal']
    print(f'losses: {len(rows)} losses;', ', '.join(f"{t} {A[t, 'n']} losses / {A[t, 'shot']} shots / {A[t, 'goal']} goals" for t in OPP))


if __name__ == '__main__':
    main()
