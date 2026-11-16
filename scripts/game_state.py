"""4. adım: ana metrikler skor durumuna göre (game_state.json).

Her olay, o andan önce atılmış gollere göre takım açısından Önde / Berabere / Geride diye etiketlenir.
Goller: sonucu Goal olan her şut (penaltı dahil) ve "Own Goal For" olayları. Metrikler build.py ile aynı
tanımla hesaplanır, ama pay ve payda skor durumuna göre ayrı toplanır; üç durumun toplamı build.py'nin
maç toplamına eşittir (script sonunda kontrol edilir). Ek olarak her durumda geçen dakika yazılır.
Girdi: match_team.json (build.py).
"""
import collections
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from clasico import OPP, PROCESSED, data  # noqa: E402
from clasico.events import game_state, is_clean_receipt, passes_before, possessions, score_before, sec, strip_after  # noqa: E402
from clasico.output import read_json, write_rows  # noqa: E402

OUT = sys.argv[1] if len(sys.argv) > 1 else PROCESSED
STATES = ('Önde', 'Berabere', 'Geride')
FIELDS = ('open_play_shots', 'passes_before_shot_sum', 'pressures', 'pressures_won_5s', 'opp_buildup_passes', 'def_actions', 'opp_controls', 'balls_stripped')


def match_states(ev, final):
    """{(takım, durum): Counter} — metriklerin pay/paydaları ve 'seconds'."""
    ev = sorted(ev, key=lambda e: e['index'])
    before, score = score_before(ev, OPP)
    for t in OPP:
        assert score[t] == final[t], ('skor tutmuyor', t, score, final)

    def state(i, t):
        return game_state(before[i], t, OPP[t])

    pos = {e['id']: i for i, e in enumerate(ev)}
    A = {(t, s): collections.Counter() for t in OPP for s in STATES}
    # Dakikalar: olay sırasında zaman damgası her zaman artmıyor; her devrede olayları zamana göre
    # sıralayıp ardışık iki olay arasındaki süreyi ilk olayın skor durumuna yazıyoruz.
    for per in (1, 2):
        idx = sorted((i for i, e in enumerate(ev) if e['period'] == per), key=lambda i: (sec(ev[i]), ev[i]['index']))
        for a, b in zip(idx, idx[1:]):
            for t in OPP:
                A[(t, state(a, t))]['seconds'] += sec(ev[b]) - sec(ev[a])
    # Şuta kadar pas (atağın ilk şutu, duran top hariç)
    for q in possessions(ev):
        sh = [e for e in q['es'] if e['type']['name'] == 'Shot' and e['shot']['type']['name'] != 'Penalty']
        if sh and q['pp'] not in ('From Corner', 'From Free Kick'):
            t = sh[0]['team']['name']
            c = A[(t, state(pos[sh[0]['id']], t))]
            c['open_play_shots'] += 1
            c['passes_before_shot_sum'] += passes_before(q['es'], sh[0])
    # Baskı verimi ve PPDA
    ts = [(e['period'], sec(e), e['possession_team']['name']) for e in ev]
    for i, e in enumerate(ev):
        n, t = e['type']['name'], e['team']['name']
        if n == 'Pressure':
            c = A[(t, state(i, t))]
            c['pressures'] += 1
            if any(p == e['period'] and sec(e) < tt <= sec(e) + 5 and pt == t for p, tt, pt in ts):
                c['pressures_won_5s'] += 1
        if n == 'Pass' and e['location'][0] <= 72:
            A[(OPP[t], state(i, OPP[t]))]['opp_buildup_passes'] += 1
        if 'location' in e and e['location'][0] >= 48 and (n in ('Interception', 'Foul Committed') or (n == 'Duel' and e['duel']['type']['name'] == 'Tackle')):
            A[(t, state(i, t))]['def_actions'] += 1
    # Sökülen top: skor durumu baskı yapan takım açısından, kontrol anında
    for i, e in enumerate(ev):
        if not is_clean_receipt(e):
            continue
        D = OPP[e['team']['name']]
        c = A[(D, state(i, D))]
        c['opp_controls'] += 1
        if strip_after(ev, i) is not None:
            c['balls_stripped'] += 1
    return A


def main():
    M = read_json(os.path.join(OUT, 'match_team.json'))
    rows = []
    for mid in sorted({m['match_id'] for m in M}):
        meta = {m['team']: m for m in M if m['match_id'] == mid}
        A = match_states(data.events(mid), {t: meta[t]['goals_for'] for t in OPP})
        for (t, s), c in A.items():
            m = meta[t]
            rows.append(dict(key=f'{mid}|{t}|{s}', match_id=mid, match=m['match'], date=m['date'], period=m['period'], coach=m['coach'],
                             team=t, state=s, minutes=round(c['seconds'] / 60, 1), **{k: c[k] for k in FIELDS}))
    # Doğrulama: üç durumun toplamı = build.py maç toplamı
    tot = collections.defaultdict(collections.Counter)
    for r in rows:
        for f in FIELDS:
            tot[(r['match_id'], r['team'])][f] += r[f]
    bad = [(m['match_id'], m['team'], f) for m in M for f in FIELDS if tot[(m['match_id'], m['team'])][f] != m[f]]
    assert not bad, bad[:5]
    write_rows(os.path.join(OUT, 'game_state.json'), rows, os.path.abspath(__file__))
    print(f'game_state: {len(rows)} satır; üç durumun toplamı maç toplamlarıyla aynı')


if __name__ == '__main__':
    main()
