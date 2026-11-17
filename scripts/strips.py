"""Step 3: balls stripped and the number of players pressing each loss (strips.json).

For every loss, count the distinct opponents with a pressure event near the ball (~11 m, 12 units) between
the receipt and the loss, plus opponents in events directly linked to the loss (duel, interception, foul).
Off-ball positions are not in event data, so this is a lower bound.
Zone and x/y are where the ball was lost, from the losing team's view. Input: match_team.json (build.py).
"""
import collections
import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from clasico import OPP, PROCESSED, data  # noqa: E402
from clasico.events import LOSS_KIND, is_clean_receipt, sec, strip_after, zone  # noqa: E402
from clasico.output import read_json, write_json  # noqa: E402

OUT = sys.argv[1] if len(sys.argv) > 1 else PROCESSED
PRESS_RADIUS = 12   # StatsBomb units, ~11 m
LINKED = ('Duel', 'Pressure', 'Interception', 'Foul Committed')


def pressers(ev_by_id, press, e, loss):
    """Ids of the distinct opponents who went to the ball."""
    defending = OPP[e['team']['name']]
    t0, t1 = sec(e), sec(loss)
    x, y = e['location'][:2]
    lx, ly = loss['location'][:2]
    who = set()
    for p in press:
        if p['period'] != e['period'] or p['team']['name'] != defending:
            continue
        ps = sec(p)
        pe = ps + p.get('duration', 0)
        if ps <= t1 + 0.5 and pe >= t0 - 0.5:
            px, py = 120 - p['location'][0], 80 - p['location'][1]   # flip the opponent's coordinates
            if min(math.hypot(px - x, py - y), math.hypot(px - lx, py - ly)) <= PRESS_RADIUS:
                who.add(p['player']['id'])
    for rid in loss.get('related_events', []):
        related = ev_by_id.get(rid)
        if (related and related['team']['name'] == defending and related['type']['name'] in LINKED
                and 'player' in related):
            who.add(related['player']['id'])
    return who


def match_strips(label, period, ev):
    by_id = {e['id']: e for e in ev}
    press = [e for e in ev if e['type']['name'] == 'Pressure']
    rows = []
    for i, e in enumerate(ev):
        if not is_clean_receipt(e):
            continue
        loss = strip_after(ev, i)
        if loss is None:
            continue
        losing_team = e['team']['name']
        lx, ly = loss['location'][:2]
        rows.append(dict(match=label, period=period, minute=e['minute'], pressing_team=OPP[losing_team],
                         losing_team=losing_team, player=e['player']['name'],
                         loss_kind=LOSS_KIND[loss['type']['name']],
                         pressers=len(pressers(by_id, press, e, loss)), zone=zone(lx, ly),
                         x=round(lx, 1), y=round(ly, 1)))
    return rows


def main():
    match_team = read_json(os.path.join(OUT, 'match_team.json'))
    matches = sorted({(m['match_id'], m['date'], m['period'], m['match']) for m in match_team}, key=lambda z: z[1])
    rows = []
    for mid, _date, period, label in matches:
        rows += match_strips(label, period, data.events(mid))
    write_json(os.path.join(OUT, 'strips.json'), rows)
    counts = collections.Counter(r['pressers'] for r in rows)
    print(f'strips: {len(rows)} balls stripped; players pressing {dict(sorted(counts.items()))}')


if __name__ == '__main__':
    main()
