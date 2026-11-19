"""Social preview card for the site (Open Graph / Twitter): docs/og.svg, standard library only.

The headline finding drawn at 1200 x 630: passes before an open-play shot per period for both clubs.
Social networks need a raster image, so docs/og.png is converted from the SVG once and committed:

    python3 site/og_image.py
    rsvg-convert -w 1200 docs/og.svg -o docs/og.png
    # macOS without librsvg: qlmanage -t -s 1200 -o /tmp docs/og.svg && sips --cropToHeightWidth 630 1200 /tmp/og.svg.png --out docs/og.png
"""
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
from clasico.output import read_json  # noqa: E402
from clasico.log import get_logger  # noqa: E402

log = get_logger('og_image')

PERIODS = ('2005-09', '2009-13', '2013-17', '2017-21')
TEAMS = (('Barcelona', '#5fb0ff'), ('Real Madrid', '#ffcb3d'))
SANS = 'font-family="Inter, Helvetica Neue, Helvetica, Arial, sans-serif"'
SERIF = 'font-family="Source Serif 4, Georgia, serif"'


def passes_per_shot(rows, team, period):
    sel = [r for r in rows if r['team'] == team and r['period'] == period]
    return sum(r['passes_before_shot_sum'] for r in sel) / sum(r['open_play_shots'] for r in sel)


def card(rows, w=1200, h=630):
    vals = {t: [passes_per_shot(rows, t, p) for p in PERIODS] for t, _ in TEAMS}
    L, R, T, B = 640, 1110, 150, 500
    x = lambda i: L + i * (R - L) / (len(PERIODS) - 1)  # noqa: E731
    ymax = max(max(v) for v in vals.values()) * 1.15
    y = lambda v: B - (B - T) * v / ymax  # noqa: E731
    o = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w} {h}">',
         '<defs><radialGradient id="a" gradientUnits="userSpaceOnUse" cx="0" cy="0" r="1" gradientTransform="translate(0 0) scale(820 700)">'
         '<stop offset="0" stop-color="#0b4ea2" stop-opacity=".7"/><stop offset="1" stop-color="#0b4ea2" stop-opacity="0"/></radialGradient>'
         f'<radialGradient id="b" gradientUnits="userSpaceOnUse" cx="0" cy="0" r="1" gradientTransform="translate({w} {h}) scale(760 600)">'
         '<stop offset="0" stop-color="#c99614" stop-opacity=".45"/><stop offset="1" stop-color="#c99614" stop-opacity="0"/></radialGradient></defs>',
         f'<rect width="{w}" height="{h}" fill="#0b1324"/><rect width="{w}" height="{h}" fill="url(#a)"/><rect width="{w}" height="{h}" fill="url(#b)"/>',
         # faint pitch markings
         f'<g fill="none" stroke="#fff" stroke-opacity=".06" stroke-width="2"><rect x="20" y="20" width="{w - 40}" height="{h - 40}"/>'
         f'<line x1="{w / 2}" y1="20" x2="{w / 2}" y2="{h - 20}"/><circle cx="{w / 2}" cy="{h / 2}" r="90"/></g>',
         f'<text x="64" y="104" {SANS} font-size="20" font-weight="600" letter-spacing="2.5" fill="#a9b3c7">EL CLÁSICO · 2005–2021</text>',
         f'<text {SERIF} font-size="64" font-weight="600" fill="#f4f6fb"><tspan x="64" y="196">Two styles</tspan>'
         '<tspan x="64" y="270">that met in</tspan><tspan x="64" y="344">the middle</tspan></text>',
         f'<text x="64" y="408" {SANS} font-size="23" fill="#d5dbe8">Passes before an open-play shot,</text>',
         f'<text x="64" y="438" {SANS} font-size="23" fill="#d5dbe8">29 La Liga Clásicos, StatsBomb data</text>']
    for t in range(0, int(ymax) + 1, 4):
        o.append(f'<line x1="{L - 20}" x2="{R + 20}" y1="{y(t):.1f}" y2="{y(t):.1f}" stroke="#fff" stroke-opacity=".08"/>')
    b, m = (vals[t] for t, _ in TEAMS)
    area = ' '.join(f'{x(i):.1f},{y(v):.1f}' for i, v in enumerate(b)) + ' ' + \
        ' '.join(f'{x(i):.1f},{y(v):.1f}' for i, v in reversed(list(enumerate(m))))
    o.append(f'<polygon points="{area}" fill="#fff" fill-opacity=".07"/>')
    for i, p in enumerate(PERIODS):
        o.append(f'<text x="{x(i):.1f}" y="{B + 44}" text-anchor="middle" {SANS} font-size="20" font-weight="600" fill="#f4f6fb">{p}</text>')
    for k, (team, colour) in enumerate(TEAMS):
        v, other = vals[team], vals[TEAMS[1 - k][0]]
        pts = ' '.join(f'{x(i):.1f},{y(q):.1f}' for i, q in enumerate(v))
        o.append(f'<polyline points="{pts}" fill="none" stroke="{colour}" stroke-width="6" stroke-linecap="round" stroke-linejoin="round"/>')
        for i, q in enumerate(v):
            dy = -20 if q >= other[i] else 36
            o.append(f'<circle cx="{x(i):.1f}" cy="{y(q):.1f}" r="9" fill="{colour}" stroke="#0b1324" stroke-width="4"/>')
            o.append(f'<text x="{x(i):.1f}" y="{y(q) + dy:.1f}" text-anchor="middle" {SANS} font-size="24" font-weight="700" fill="{colour}">{q:.1f}</text>')
        o.append(f'<text x="{L - 20}" y="{T - 50 + 30 * k}" {SANS} font-size="21" font-weight="700" fill="{colour}">● {team}</text>')
    o.append(f'<text x="64" y="{h - 52}" {SANS} font-size="19" fill="#a9b3c7">arslannizzetali.github.io/el-clasico-analytics</text>')
    o.append('</svg>')
    return '\n'.join(o) + '\n'


def main():
    out = os.path.join(ROOT, 'docs', 'og.svg')
    with open(out, 'w', encoding='utf-8') as fh:
        fh.write(card(read_json(os.path.join(ROOT, 'data', 'processed', 'match_team.json'))))
    log.info('social card written', extra={'path': 'docs/og.svg'})


if __name__ == '__main__':
    main()
