"""Final La Liga tables 2004/05-2020/21 from every result of each season, and the clubs that finished
in the top 10 most often.

Input: engsoccerdata (github.com/jalapic/engsoccerdata), every Spanish top-flight result.
Output: data/reference/standings.csv (team names in StatsBomb spelling), loaded by scripts/load_db.py.

Ranking follows La Liga's rules: points, then the head-to-head mini-league between tied clubs
(points, then goal difference), then overall goal difference, then goals scored.
"""
import collections
import csv
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from clasico import RAW, ROOT, data  # noqa: E402

URL = 'https://raw.githubusercontent.com/jalapic/engsoccerdata/master/data-raw/spain.csv'
OUT = os.path.join(ROOT, 'data', 'reference', 'standings.csv')
FIRST, LAST = 2004, 2020   # season start years
NAMES = {
    'Albacete': 'Albacete', 'Athletic Bilbao': 'Athletic Club', 'Atletico Madrid': 'Atlético Madrid',
    'CA Osasuna': 'Osasuna', 'CD Alaves': 'Deportivo Alavés', 'CD Leganes': 'Leganés',
    'CD Numancia': 'CD Numancia de Soria', 'CD Tenerife': 'Tenerife', 'Cadiz CF': 'Cádiz', 'Celta Vigo': 'Celta Vigo',
    'Cordoba CF': 'Córdoba CF', 'Deportivo La Coruna': 'RC Deportivo La Coruña', 'Elche CF': 'Elche',
    'Espanyol Barcelona': 'Espanyol', 'FC Barcelona': 'Barcelona', 'Getafe CF': 'Getafe',
    'Gimnastic': 'Gimnàstic Tarragona', 'Girona': 'Girona', 'Granada CF': 'Granada', 'Hercules CF': 'Hércules',
    'Levante UD': 'Levante UD', 'Malaga CF': 'Málaga', 'RCD Mallorca': 'Mallorca',
    'Racing Santander': 'Racing Santander', 'Rayo Vallecano': 'Rayo Vallecano', 'Real Betis': 'Real Betis',
    'Real Madrid': 'Real Madrid', 'Real Murcia': 'Real Murcia CF', 'Real Sociedad': 'Real Sociedad',
    'Real Valladolid': 'Real Valladolid', 'Real Zaragoza': 'Real Zaragoza', 'Recreativo Huelva': 'Recreativo Huelva',
    'SD Eibar': 'Eibar', 'SD Huesca': 'Huesca', 'Sevilla FC': 'Sevilla', 'Sporting Gijon': 'Sporting Gijón',
    'UD Almeria': 'Almería', 'UD Las Palmas': 'Las Palmas', 'Valencia CF': 'Valencia', 'Villarreal CF': 'Villarreal',
    'Xerez CD': 'Xerez',
}


def table(results):
    """results: [(home, away, home_goals, away_goals)] -> rows sorted by final position."""
    t = collections.defaultdict(lambda: dict(played=0, won=0, drawn=0, lost=0, goals_for=0, goals_against=0, points=0))
    for h, a, hg, ag in results:
        for team, gf, ga in ((h, hg, ag), (a, ag, hg)):
            r = t[team]
            r['played'] += 1
            r['goals_for'] += gf
            r['goals_against'] += ga
            k = 'won' if gf > ga else 'drawn' if gf == ga else 'lost'
            r[k] += 1
            r['points'] += {'won': 3, 'drawn': 1, 'lost': 0}[k]

    def h2h(group):
        m = collections.Counter()
        for h, a, hg, ag in results:
            if h in group and a in group:
                m[h, 'p'] += 3 if hg > ag else 1 if hg == ag else 0
                m[a, 'p'] += 3 if ag > hg else 1 if hg == ag else 0
                m[h, 'gd'] += hg - ag
                m[a, 'gd'] += ag - hg
        return m

    by_pts = collections.defaultdict(list)
    for team, r in t.items():
        by_pts[r['points']].append(team)
    order = []
    for pts in sorted(by_pts, reverse=True):
        group = by_pts[pts]
        m = h2h(set(group))
        order += sorted(group, key=lambda x: (-m[x, 'p'], -m[x, 'gd'], -(t[x]['goals_for'] - t[x]['goals_against']),
                                              -t[x]['goals_for'], x))
    return [dict(position=i + 1, team_name=team, **t[team]) for i, team in enumerate(order)]


def main():
    src = data.fetch(URL, os.path.join(RAW, 'engsoccerdata_spain.csv'))
    by_season = collections.defaultdict(list)
    with open(src, encoding='utf-8') as fh:
        for r in csv.DictReader(fh):
            y = int(r['Season'])
            if FIRST <= y <= LAST and r['tier'] == '1':
                by_season[y].append((NAMES[r['home']], NAMES[r['visitor']], int(r['hgoal']), int(r['vgoal'])))
    rows = []
    for y in sorted(by_season):
        assert len(by_season[y]) == 380, (y, len(by_season[y]))
        rows += [dict(season_name=f'{y}/{y + 1}', **r) for r in table(by_season[y])]
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, 'w', newline='', encoding='utf-8') as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)
    print(f'standings: {len(by_season)} seasons, {len(rows)} rows -> {os.path.relpath(OUT, ROOT)}')


if __name__ == '__main__':
    main()
