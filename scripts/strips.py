"""3. adım: sökülen toplar ve baskıya giden oyuncu sayısı (strips.json).

Her kayıp için, top kontrolünden kayba kadar geçen sürede topun yakınında (~11 m, 12 birim) baskı olayı
kaydedilmiş farklı rakip oyuncular ve kayba doğrudan bağlı rakip olayları (ikili mücadele, top kesme, faul)
sayılır. Topsuz oyuncuların konumu veride olmadığı için bu bir alt sınırdır.
Bölge ve x/y topu kaptıran takımın gözünden, kaybın olduğu nokta. Girdi: match_team.json (build.py).
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
PRESS_RADIUS = 12   # StatsBomb birimi, ~11 m
LINKED = ('Duel', 'Pressure', 'Interception', 'Foul Committed')


def pressers(ev_by_id, press, e, L):
    """Kayba giden farklı rakip oyuncuların id kümesi."""
    D = OPP[e['team']['name']]
    t0, t1 = sec(e), sec(L)
    x, y = e['location'][:2]
    lx, ly = L['location'][:2]
    who = set()
    for p in press:
        if p['period'] != e['period'] or p['team']['name'] != D:
            continue
        ps = sec(p)
        pe = ps + p.get('duration', 0)
        if ps <= t1 + 0.5 and pe >= t0 - 0.5:
            px, py = 120 - p['location'][0], 80 - p['location'][1]   # rakibin koordinatını çevir
            if min(math.hypot(px - x, py - y), math.hypot(px - lx, py - ly)) <= PRESS_RADIUS:
                who.add(p['player']['id'])
    for rid in L.get('related_events', []):
        r = ev_by_id.get(rid)
        if r and r['team']['name'] == D and r['type']['name'] in LINKED and 'player' in r:
            who.add(r['player']['id'])
    return who


def match_strips(label, period, ev):
    by_id = {e['id']: e for e in ev}
    press = [e for e in ev if e['type']['name'] == 'Pressure']
    rows = []
    for i, e in enumerate(ev):
        if not is_clean_receipt(e):
            continue
        L = strip_after(ev, i)
        if L is None:
            continue
        TA = e['team']['name']
        lx, ly = L['location'][:2]
        rows.append(dict(mac=label, donem=period, dakika=e['minute'], baski_yapan=OPP[TA], topu_kaptiran_takim=TA,
                         oyuncu=e['player']['name'], kayip_turu=LOSS_KIND[L['type']['name']],
                         baskiya_giden=len(pressers(by_id, press, e, L)), bolge=zone(lx, ly), x=round(lx, 1), y=round(ly, 1)))
    return rows


def main():
    M = read_json(os.path.join(OUT, 'match_team.json'))
    rows = []
    for mid, date, period, label in sorted({(m['match_id'], m['date'], m['period'], m['match']) for m in M}, key=lambda z: z[1]):
        rows += match_strips(label, period, data.events(mid))
    write_json(os.path.join(OUT, 'strips.json'), rows)
    c = collections.Counter(r['baskiya_giden'] for r in rows)
    print(f'strips: {len(rows)} sökülen top; baskıya giden oyuncu dağılımı {dict(sorted(c.items()))}')


if __name__ == '__main__':
    main()
