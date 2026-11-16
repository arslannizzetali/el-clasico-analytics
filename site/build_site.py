"""Builds the public single-file version of the dashboard: docs/index.html (GitHub Pages).

The working dashboard page (dashboard/index.html) is used as is; the small `dash` API it expects (data,
calculations, drawings) is provided here in the browser and the data is embedded in the file. Both versions
therefore run the same code and their numbers cannot drift apart.

    python3 site/build_site.py
"""
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
from clasico.output import read_json, read_rows  # noqa: E402

D3 = 'https://cdnjs.cloudflare.com/ajax/libs/d3/7.8.5/d3.min.js'
P = lambda n: os.path.join(ROOT, 'data', 'processed', n)  # noqa: E731

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

FOOT = """<footer class="site-foot">Data: <a href="https://github.com/statsbomb/open-data">StatsBomb Open Data</a>.
Built from the project's Python pipeline; every metric is defined in the
<a href="https://github.com/arslannizzetali/el-clasico-analytics">README</a>.</footer>"""


def main():
    page = open(os.path.join(ROOT, 'dashboard', 'index.html'), encoding='utf-8').read()
    data = {'match_team': read_json(P('match_team.json')), 'shots': read_json(P('shots.json')),
            'losses': read_rows(P('losses_ds.json')), 'game_state': read_rows(P('game_state.json')),
            'uncertainty': read_rows(P('uncertainty.json'))}
    i = page.index('<script>')
    html = ('<!doctype html><html lang="en"><head><meta charset="utf-8">'
            '<meta name="viewport" content="width=device-width,initial-scale=1">'
            '<title>El Clásico tactical analysis, 2005-2021</title>'
            '<meta name="description" content="How El Clásico changed over 16 years, match by match and on the pitch: 29 Real Madrid - Barcelona La Liga games, StatsBomb open data.">'
            '<link rel="preconnect" href="https://fonts.googleapis.com">'
            '<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;600&family=Source+Serif+4:wght@400;600&display=swap" rel="stylesheet">'
            f'<style>{TOKENS}</style>'
            f'<script src="{D3}"></script>'
            f'<script>window.__DATA={json.dumps(data, ensure_ascii=False, separators=(",", ":"))};{SHIM}</script>'
            '</head><body>'
            f'<div id="dash-root">{page[:i]}</div>{FOOT}'
            f'{page[i:]}'
            '<script>window.__dashAll();</script>'
            '</body></html>')
    out = os.path.join(ROOT, 'docs', 'index.html')
    os.makedirs(os.path.dirname(out), exist_ok=True)
    with open(out, 'w', encoding='utf-8') as fh:
        fh.write(html)
    print(f'docs/index.html written ({len(html) / 1e6:.1f} MB)')


if __name__ == '__main__':
    main()
