"""README için üç bulgu grafiği (SVG, sadece standart kütüphane): docs/img/*.svg

    python3 site/readme_charts.py
"""
import collections
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
from clasico.events import zone  # noqa: E402
from clasico.output import read_json, read_rows  # noqa: E402

OUT = os.path.join(ROOT, 'docs', 'img')
PERIODS = ('2005-09', '2009-13', '2013-17', '2017-21')
BLUE, GREY, INK, MUTED, GRID, BG = '#2563eb', '#8b929c', '#15171a', '#5c6470', '#e9ecef', '#ffffff'
FONT = 'font-family="Inter, -apple-system, Segoe UI, Roboto, sans-serif"'
P = lambda n: os.path.join(ROOT, 'data', 'processed', n)  # noqa: E731
fmt = lambda v: f'{v:.1f}'  # noqa: E731


def ratio(rows, a, b, k=1):
    return k * sum(r[a] for r in rows) / sum(r[b] for r in rows)


def line_chart(title, subtitle, series, ymax, note, path, w=720, h=380):
    """series: [(etiket, renk, [4 değer], kalın?)]"""
    L, R, T, B = 56, 150, 86, 64
    x = lambda i: L + i * (w - L - R) / (len(PERIODS) - 1)  # noqa: E731
    y = lambda v: T + (h - T - B) * (1 - v / ymax)  # noqa: E731
    o = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w} {h}" width="{w}" height="{h}" {FONT}>',
         f'<rect width="{w}" height="{h}" rx="12" fill="{BG}"/>',
         f'<text x="24" y="36" font-size="19" font-weight="600" fill="{INK}">{title}</text>',
         f'<text x="24" y="60" font-size="13.5" fill="{MUTED}">{subtitle}</text>']
    step = 5 if ymax > 12 else 2
    for t in range(0, int(ymax) + 1, step):
        o.append(f'<line x1="{L}" x2="{w - R + 20}" y1="{y(t):.1f}" y2="{y(t):.1f}" stroke="{GRID}"/>')
        o.append(f'<text x="{L - 10}" y="{y(t) + 4:.1f}" font-size="12" fill="{MUTED}" text-anchor="end">{t}</text>')
    for i, p in enumerate(PERIODS):
        o.append(f'<text x="{x(i):.1f}" y="{h - B + 24}" font-size="12.5" fill="{MUTED}" text-anchor="middle">{p}</text>')
    # iki seri: her dönemde değeri yüksek olanın etiketi üstte, düşük olanınki altta
    for s_i, (label, color, vals, bold) in enumerate(series):
        pts = ' '.join(f'{x(i):.1f},{y(v):.1f}' for i, v in enumerate(vals))
        o.append(f'<polyline points="{pts}" fill="none" stroke="{color}" stroke-width="{3.5 if bold else 2.5}" stroke-linejoin="round" stroke-linecap="round"/>')
        for i, v in enumerate(vals):
            other = series[1 - s_i][2][i]
            dy = -12 if v >= other else 21
            o.append(f'<circle cx="{x(i):.1f}" cy="{y(v):.1f}" r="{5.5 if bold else 4.5}" fill="{color}" stroke="{BG}" stroke-width="2"/>')
            o.append(f'<text x="{x(i):.1f}" y="{y(v) + dy:.1f}" font-size="12.5" font-weight="600" fill="{color}" text-anchor="middle">{fmt(v)}</text>')
    # seri adları sağda, birbirine en az 18 px uzak
    ends = sorted(((y(v[-1]), lab, col) for lab, col, v, _ in series))
    if ends[1][0] - ends[0][0] < 18:
        mid = (ends[0][0] + ends[1][0]) / 2
        ends = [(mid - 9, ends[0][1], ends[0][2]), (mid + 9, ends[1][1], ends[1][2])]
    for yy, lab, col in ends:
        o.append(f'<text x="{x(3) + 16:.1f}" y="{yy + 4:.1f}" font-size="13" font-weight="600" fill="{col}">{lab}</text>')
    o.append(f'<text x="24" y="{h - 10}" font-size="11.5" fill="{MUTED}">{note}</text>')
    o.append('</svg>')
    with open(path, 'w', encoding='utf-8') as fh:
        fh.write('\n'.join(o))


def zone_chart(L, path, w=720, h=346):
    """Kayıp bölgesine göre rakip şutuyla bitme oranı, iki takım yan yana."""
    o = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w} {h}" width="{w}" height="{h}" {FONT}>',
         f'<rect width="{w}" height="{h}" rx="12" fill="{BG}"/>',
         f'<text x="24" y="36" font-size="19" font-weight="600" fill="{INK}">Where losing the ball costs a shot</text>',
         f'<text x="24" y="60" font-size="13.5" fill="{MUTED}">Share of balls lost after a controlled touch that end in an opponent shot within 20 s, by zone</text>']
    pw, ph = 300, 200
    for k, team in enumerate(('Barcelona', 'Real Madrid')):
        ox, oy = 24 + k * (pw + 72), 96
        rows = [r for r in L if r['team'] == team]
        n, s = collections.Counter(), collections.Counter()
        for r in rows:
            z = zone(r['x'], r['y'])
            n[z] += 1
            s[z] += r['shot']
        o.append(f'<text x="{ox}" y="{oy - 10}" font-size="14" font-weight="600" fill="{INK}">{team}</text>')
        o.append(f'<text x="{ox + pw}" y="{oy - 10}" font-size="11.5" fill="{MUTED}" text-anchor="end">attacking →</text>')
        for z in range(1, 10):
            c, lane = (z - 1) // 3, (z - 1) % 3
            zx, zy = ox + c * pw / 3, oy + lane * ph / 3   # dashboard ile aynı yön
            pct = 100 * s[z] / n[z] if n[z] else 0
            few = n[z] < 20
            op = 0.06 + 0.8 * min(pct, 15) / 15
            fill = f'fill="#eceef1"' if few else f'fill="{BLUE}" fill-opacity="{op:.2f}"'
            o.append(f'<rect x="{zx:.1f}" y="{zy:.1f}" width="{pw / 3:.1f}" height="{ph / 3:.1f}" {fill} stroke="{BG}" stroke-width="2"/>')
            label = f'{pct:.0f}%'
            col = MUTED if few else BG if op > 0.5 else INK
            o.append(f'<text x="{zx + pw / 6:.1f}" y="{zy + ph / 6 + 2:.1f}" font-size="17" font-weight="600" fill="{col}" text-anchor="middle">{label}</text>')
            o.append(f'<text x="{zx + pw / 6:.1f}" y="{zy + ph / 6 + 19:.1f}" font-size="11" fill="{col}" text-anchor="middle">{s[z]}/{n[z]}</text>')
        o.append(f'<rect x="{ox}" y="{oy}" width="{pw}" height="{ph}" fill="none" stroke="{GREY}" stroke-width="1.2"/>')
    o.append(f'<text x="24" y="{h - 28}" font-size="11.5" fill="{MUTED}">29 La Liga Clásicos, 2005-2021 · StatsBomb Open Data. 9 equal zones, seen from the team losing the ball.</text>')
    o.append(f'<text x="24" y="{h - 12}" font-size="11.5" fill="{MUTED}">Grey: fewer than 20 losses in the zone, too few to read as a rate.</text>')
    o.append('</svg>')
    with open(path, 'w', encoding='utf-8') as fh:
        fh.write('\n'.join(o))


def main():
    os.makedirs(OUT, exist_ok=True)
    M, G, L = read_json(P('match_team.json')), read_rows(P('game_state.json')), read_rows(P('losses_ds.json'))
    pps = lambda t: [ratio([m for m in M if m['team'] == t and m['period'] == p], 'passes_before_shot_sum', 'open_play_shots') for p in PERIODS]  # noqa: E731
    line_chart('The two styles converged', 'Completed passes before an open-play shot, per period',
               [('Barcelona', BLUE, pps('Barcelona'), True), ('Real Madrid', GREY, pps('Real Madrid'), False)],
               14, '29 La Liga Clásicos, 2005-2021 · StatsBomb Open Data · first shot of each possession, set pieces excluded',
               os.path.join(OUT, 'convergence.svg'))
    ppda_all = [ratio([m for m in M if m['team'] == 'Barcelona' and m['period'] == p], 'opp_buildup_passes', 'def_actions') for p in PERIODS]
    ppda_lvl = [ratio([g for g in G if g['team'] == 'Barcelona' and g['period'] == p and g['state'] == 'Berabere'], 'opp_buildup_passes', 'def_actions') for p in PERIODS]
    line_chart("Barcelona's press faded, regardless of the score", 'PPDA: opponent build-up passes per defensive action (higher = less pressure)',
               [('Score level', BLUE, ppda_lvl, True), ('All minutes', GREY, ppda_all, False)],
               22, 'In 2017-21 Barcelona led for only 20% of the minutes, so sitting on a lead does not explain the rise.',
               os.path.join(OUT, 'press.svg'))
    zone_chart(L, os.path.join(OUT, 'zones.svg'))
    print('docs/img: convergence.svg, press.svg, zones.svg')


if __name__ == '__main__':
    main()
