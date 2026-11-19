"""Builds the public single-file version of the dashboard: docs/index.html (GitHub Pages).

The working dashboard page (dashboard/index.html) is used as is; the small `dash` API it expects (data,
calculations, drawings) is provided here in the browser and the data is embedded in the file. Both versions
therefore run the same code and their numbers cannot drift apart.

    python3 site/build_site.py
"""
import csv
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
from clasico.output import read_json, read_rows  # noqa: E402
from clasico.log import get_logger  # noqa: E402

log = get_logger('build_site')

D3 = 'https://cdnjs.cloudflare.com/ajax/libs/d3/7.8.5/d3.min.js'
P = lambda n: os.path.join(ROOT, 'data', 'processed', n)  # noqa: E731
L = lambda n: os.path.join(ROOT, 'data', 'league', n)  # noqa: E731
CATEGORIES = ('clasico', 'barcelona_vs_top10', 'barcelona_all', 'season_2015_16', 'ucl_finals')
LEAGUE_FIELDS = ('match_id', 'match_date', 'season_name', 'period', 'team', 'opponent', 'venue', 'goals_for',
                 'goals_against', 'coach', 'formation', 'formation_changes', 'passes_before_shot_sum', 'open_play_shots',
                 'pressures_won_5s', 'pressures', 'opp_buildup_passes', 'def_actions', 'possession_pct',
                 'pass_interval_s', 'attack_speed_mps', 'np_xg')
TEXT = {'match_date', 'season_name', 'period', 'team', 'opponent', 'venue', 'coach', 'formation'}

TOKENS = """
:root{color-scheme:light;
 --font-anthropic-sans:"Inter",system-ui,-apple-system,"Segoe UI",Roboto,sans-serif;
 --font-anthropic-serif:"Source Serif 4",Georgia,serif;
 --cds-font-size-title:30px;--cds-font-size-heading:19px;--cds-font-size-body:15px;--cds-font-size-caption:13px;
 --cds-font-weight-medium:600;--cds-radius:10px;
 --cds-gap-xs:4px;--cds-gap-sm:8px;--cds-gap-md:12px;--cds-gap-lg:16px;--cds-gap-xl:24px;--cds-pad-lg:20px;
 --page-bg:#f6f7f9;--color-panel:#ffffff;--color-fg:#15171a;--color-fg-muted:#5c6470;--color-border-line:#e3e6ea;
 --color-bad:#dc2626;--color-bg-subtle:rgba(37,99,235,.07);
 --cds-chart-axis:#9aa1ab;--cds-chart-grid:#eef0f3;--cds-chart-muted:#a3a9b2;--cds-chart-reference:#3b4048;
 --cds-text-secondary:#5c6470;--cds-surface-popover:#ffffff;--cds-border:#d5d9df;--cds-shadow-popover:0 4px 14px rgba(0,0,0,.12)}
@media (prefers-color-scheme:dark){:root{color-scheme:dark;
 --page-bg:#0f1115;--color-panel:#171a20;--color-fg:#eceef1;--color-fg-muted:#a0a7b2;--color-border-line:#2a2f37;
 --color-bad:#f05252;--color-bg-subtle:rgba(96,140,255,.12);
 --cds-chart-axis:#5d6470;--cds-chart-grid:#232831;--cds-chart-muted:#6b7380;--cds-chart-reference:#c9ced6;
 --cds-text-secondary:#a0a7b2;--cds-surface-popover:#1f232b;--cds-border:#363c46;--cds-shadow-popover:0 4px 14px rgba(0,0,0,.5)}}
html,body{margin:0;background:var(--page-bg)}
#dash-root{max-width:1120px;margin:0 auto;padding:24px 16px 48px;box-sizing:border-box}
.site-foot{max-width:1120px;margin:0 auto;padding:0 16px 32px;box-sizing:border-box;font:13px/1.5 var(--font-anthropic-sans);color:var(--color-fg-muted)}
.site-foot a{color:inherit}
select.dash-select{font:inherit;padding:6px 8px;border-radius:8px;border:1px solid var(--color-border-line);background:var(--color-panel);color:var(--color-fg);max-width:100%}
"""

SHIM = r"""
(function(){
  const DATA = window.__DATA, draws = {}, calcs = {}, cache = {};
  const runDraw = (name) => document.querySelectorAll('[data-draw="' + name + '"]').forEach((el) => {
    if (el.closest('[hidden]')) return;
    try { draws[name] && draws[name](el); } catch (e) { console.error(name, e); }
  });
  window.dash = {
    data(id) {
      if (DATA[id]) return {status: 'ok', data: DATA[id], columns: Object.keys(DATA[id][0] || {})};
      if (calcs[id]) {
        if (!(id in cache)) cache[id] = calcs[id].fn(...calcs[id].inputs.map((i) => dash.data(i).data));
        return {status: 'ok', data: cache[id]};
      }
      return {status: 'missing', data: []};
    },
    calc(id, o) { calcs[id] = o; },
    loader() {},
    draw(name, fn) { if (typeof fn === 'function') { draws[name] = fn; return; } runDraw(name); },
    onData(fn) { fn(); }, colors: [], params: () => ({}), setParams() {}, resetParams() {}, setLink() {}, refresh() {},
  };
  window.__dashAll = () => Object.keys(draws).forEach(runDraw);
  // redraw sections that become visible (when the view, team or score state changes)
  const mo = new MutationObserver((list) => { if (list.some((m) => m.attributeName === 'hidden')) requestAnimationFrame(window.__dashAll); });
  window.addEventListener('DOMContentLoaded', () => mo.observe(document.getElementById('dash-root'), {attributes: true, subtree: true, attributeFilter: ['hidden']}));
  let w = 0;
  window.addEventListener('resize', () => { if (Math.abs(innerWidth - w) > 20) { w = innerWidth; window.__dashAll(); } });
})();
"""

NAV = """<nav class="lg-nav" aria-label="Sections"><p class="lg-brand">El Clásico in La Liga · StatsBomb open data</p>
<div class="ec-seg" role="tablist">
<button type="button" class="lg-tabbtn" role="tab" data-go="clasico" aria-selected="true">El Clásico</button>
<button type="button" class="lg-tabbtn" role="tab" data-go="league" aria-selected="false">League context</button>
<button type="button" class="lg-tabbtn" role="tab" data-go="seasons" aria-selected="false">Special seasons</button>
<button type="button" class="lg-tabbtn" role="tab" data-go="finals" aria-selected="false">UCL finals</button>
</div></nav>"""

FOOT = """<footer class="site-foot">Data: <a href="https://github.com/statsbomb/open-data">StatsBomb Open Data</a>.
Built from the project's Python pipeline; every metric is defined in the
<a href="https://github.com/arslannizzetali/el-clasico-analytics">README</a>.</footer>"""


def _csv(path):
    with open(path, encoding='utf-8') as fh:
        return list(csv.DictReader(fh))


def _num(v):
    if v == '':
        return None
    f = float(v)
    return int(f) if f.is_integer() else f


def columnar(rows):
    """[{...}, ...] -> {cols, rows}: field names once, values as arrays (the page expands them back)."""
    cols = list(rows[0])
    return [{'cols': cols, 'rows': [[r[c] for c in cols] for r in rows]}]


def league_data():
    """The league-wide tables (data/league, written by analysis/league.py and intervals.py) for the League
    and Special seasons tabs: one row per team per match, with the categories the match belongs to."""
    rows, cats = {}, {}
    for cat in CATEGORIES:
        for r in _csv(L(f'match_team_{cat}.csv')):
            rows[(r['match_id'], r['team'])] = {f: (r[f] or None) if f in TEXT else _num(r[f]) for f in LEAGUE_FIELDS}
            if cat not in cats.setdefault(r['match_id'], []):
                cats[r['match_id']].append(cat)
    out = sorted(rows.values(), key=lambda r: (r['match_date'], r['match_id'], r['venue'] != 'Home'))
    for r in out:
        r['cats'] = '|'.join(cats[str(r['match_id'])])
    by_club = {}
    for r in _csv(os.path.join(ROOT, 'data', 'reference', 'standings.csv')):
        by_club.setdefault(r['team_name'], []).append(int(r['position']))
    finishes = {t: sum(p <= 10 for p in ps) for t, ps in by_club.items()}
    top = sorted(by_club, key=lambda t: (-finishes[t], sum(by_club[t]) / len(by_club[t])))[:10]
    shifts = [{k: (_num(v) if k in ('match_id', 'period', 'minute', 'starting') else v) for k, v in r.items()}
              for r in _csv(L('tactical_shifts.csv'))]
    intervals = [{k: (_num(v) if k in ('matches', 'value', 'lo', 'hi', 'clear') else v) for k, v in r.items()}
                 for r in _csv(L('intervals.csv'))]
    finals = [{k: (_num(v) if k not in ('match_date', 'season_name', 'team', 'opponent', 'metric', 'basis') else v)
               for k, v in r.items()} for r in _csv(L('finals.csv'))]
    return {'league_raw': columnar(out), 'league_intervals_raw': columnar(intervals), 'ucl_finals_raw': columnar(finals),
            'tactical_shifts_raw': columnar(shifts),
            'league_meta': [{'top_clubs': top, 'top_finishes': {t: finishes[t] for t in top}}]}


def main():
    page = open(os.path.join(ROOT, 'dashboard', 'index.html'), encoding='utf-8').read()
    data = {'match_team': read_json(P('match_team.json')), 'shots': read_json(P('shots.json')),
            'losses': read_rows(P('losses_ds.json')), 'game_state': read_rows(P('game_state.json')),
            'uncertainty': read_rows(P('uncertainty.json')), **league_data()}
    league = open(os.path.join(ROOT, 'dashboard', 'league.html'), encoding='utf-8').read()
    style = league[league.index('<style>'):league.index('</style>') + len('</style>')]
    tab = lambda name: league[league.index(f'<!--tab:{name}-->') + len(f'<!--tab:{name}-->'):league.index('<!--/tab-->', league.index(f'<!--tab:{name}-->'))]  # noqa: E731
    script = league[league.index('<script>'):]
    i = page.index('<script>')
    html = ('<!doctype html><html lang="en"><head><meta charset="utf-8">'
            '<meta name="viewport" content="width=device-width,initial-scale=1">'
            '<title>El Clásico in La Liga, 2004-2021</title>'
            '<meta name="description" content="How El Clásico changed over 16 years, and how it compares with the rest of La Liga: '
            '29 Real Madrid - Barcelona matches, 524 Barcelona league matches, the full 2015/16 season and seven Champions League finals, StatsBomb open data.">'
            '<link rel="preconnect" href="https://fonts.googleapis.com">'
            '<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;600&family=Source+Serif+4:wght@400;600&display=swap" rel="stylesheet">'
            f'<style>{TOKENS}</style>{style}'
            f'<script src="{D3}"></script>'
            f'<script>window.__DATA={json.dumps(data, ensure_ascii=False, separators=(",", ":"))};{SHIM}</script>'
            '</head><body>'
            f'<div id="dash-root">{NAV}'
            f'<div data-tab="clasico">{page[:i]}</div>'
            f'<div data-tab="league" hidden>{tab("league")}</div>'
            f'<div data-tab="seasons" hidden>{tab("seasons")}</div>'
            f'<div data-tab="finals" hidden>{tab("finals")}</div>'
            f'</div>{FOOT}'
            f'{page[i:]}{script}'
            '<script>window.__dashAll();</script>'
            '</body></html>')
    out = os.path.join(ROOT, 'docs', 'index.html')
    os.makedirs(os.path.dirname(out), exist_ok=True)
    with open(out, 'w', encoding='utf-8') as fh:
        fh.write(html)
    log.info('site written', extra={'path': 'docs/index.html', 'mb': round(len(html) / 1e6, 2)})


if __name__ == '__main__':
    main()
