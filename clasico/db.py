"""PostgreSQL access: connection, schema, and loading StatsBomb matches with COPY.

Needs the packages in requirements.txt; the reference pipeline does not import this module."""
import csv
import json
import os

import psycopg

from . import ROOT
from .events import sec

DEFAULT_URL = 'postgresql+psycopg://clasico:clasico@localhost:5434/clasico'
SCHEMA = os.path.join(ROOT, 'db', 'schema.sql')
STANDINGS = os.path.join(ROOT, 'data', 'reference', 'standings.csv')


def url():
    """SQLAlchemy URL from DATABASE_URL (see .env.example)."""
    return os.environ.get('DATABASE_URL', DEFAULT_URL)


def connect():
    """A plain psycopg connection (the SQLAlchemy driver suffix is dropped)."""
    return psycopg.connect(url().replace('postgresql+psycopg://', 'postgresql://'))


def engine():
    """SQLAlchemy engine, for pandas.read_sql."""
    import sqlalchemy
    return sqlalchemy.create_engine(url())


def apply_schema(conn):
    with open(SCHEMA, encoding='utf-8') as fh:
        conn.execute(fh.read())


def _detail(e):
    """The type-specific part of an event, e.g. e['pass'] for a Pass, e['ball_receipt'] for a Ball Receipt*."""
    key = e['type']['name'].lower().replace('*', '').replace(' ', '_')
    d = e.get(key)
    return d if isinstance(d, dict) else {}


def event_row(match_id, e):
    d = _detail(e)
    loc, end = e.get('location') or [None, None], d.get('end_location') or [None, None, None]
    return (e['id'], match_id, e['index'], e['period'], e['minute'], e['second'], sec(e), e['type']['name'],
            e['team']['id'], e.get('player', {}).get('id'), e['possession'], e['possession_team']['id'],
            e['play_pattern']['name'], loc[0], loc[1], end[0], end[1],
            d.get('outcome', {}).get('name'), d.get('type', {}).get('name'), d.get('statsbomb_xg'),
            e.get('duration'), bool(e.get('under_pressure')), json.dumps(e, ensure_ascii=False))


EVENT_COLS = ('event_id, match_id, idx, period, minute, second, ts, type, team_id, player_id, possession, '
              'possession_team_id, play_pattern, x, y, end_x, end_y, outcome, subtype, xg, duration, under_pressure, raw')


def _manager(team):
    m = team.get('managers') or []
    return (m[0].get('nickname') or m[0]['name']) if m else None


def load_match(conn, g, ev, lineup):
    """Replace one match (row, lineups, events) inside the caller's transaction."""
    mid = g['match_id']
    h, a = g['home_team'], g['away_team']
    teams = {h['home_team_id']: h['home_team_name'], a['away_team_id']: a['away_team_name']}
    teams.update({e['team']['id']: e['team']['name'] for e in ev})
    players = {e['player']['id']: e['player']['name'] for e in ev if 'player' in e}
    for side in lineup:
        teams[side['team_id']] = side['team_name']
        players.update({p['player_id']: p['player_name'] for p in side['lineup']})

    conn.execute('DELETE FROM matches WHERE match_id = %s', (mid,))
    with conn.cursor() as cur:
        cur.executemany('INSERT INTO teams VALUES (%s, %s) ON CONFLICT DO NOTHING', list(teams.items()))
        cur.executemany('INSERT INTO players VALUES (%s, %s) ON CONFLICT DO NOTHING', list(players.items()))
        c, s = g['competition'], g['season']
        cur.execute('INSERT INTO competitions VALUES (%s, %s, %s, %s) ON CONFLICT DO NOTHING',
                    (c['competition_id'], s['season_id'], c['competition_name'], s['season_name']))
        cur.execute('INSERT INTO matches (match_id, competition_id, season_id, season_name, match_date, match_week, '
                    'home_team_id, away_team_id, home_score, away_score, home_manager, away_manager, stadium, referee) '
                    'VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)',
                    (mid, c['competition_id'], s['season_id'], s['season_name'], g['match_date'], g.get('match_week'),
                     h['home_team_id'], a['away_team_id'], g['home_score'], g['away_score'], _manager(h), _manager(a),
                     (g.get('stadium') or {}).get('name'), (g.get('referee') or {}).get('name')))
        with cur.copy('COPY lineups FROM STDIN') as cp:
            for side in lineup:
                for p in side['lineup']:
                    cp.write_row((mid, side['team_id'], p['player_id'], p.get('jersey_number'),
                                  json.dumps(p.get('positions', []), ensure_ascii=False)))
        with cur.copy(f'COPY events ({EVENT_COLS}) FROM STDIN') as cp:
            for e in ev:
                cp.write_row(event_row(mid, e))


def load_standings(conn, path=STANDINGS):
    with open(path, encoding='utf-8') as fh:
        rows = list(csv.DictReader(fh))
    conn.execute('DELETE FROM standings')
    with conn.cursor().copy('COPY standings (season_name, position, team_name, played, won, drawn, lost, '
                            'goals_for, goals_against, points) FROM STDIN') as cp:
        for r in rows:
            cp.write_row([r[k] for k in ('season_name', 'position', 'team_name', 'played', 'won', 'drawn', 'lost',
                                         'goals_for', 'goals_against', 'points')])


# Every category is one SQL query over the loaded matches. A match can be in several.
CATEGORIES = {
    # The 29 Real Madrid - Barcelona matches the reference pipeline analyses (2005/06 on)
    'clasico': """
        SELECT match_id FROM match_list
        WHERE 'Real Madrid' IN (home, away) AND 'Barcelona' IN (home, away) AND season_name >= '2005'""",
    'barcelona_all': """
        SELECT match_id FROM match_list WHERE 'Barcelona' IN (home, away)""",
    'barcelona_vs_top10': """
        SELECT match_id FROM match_list
        WHERE 'Barcelona' IN (home, away)
          AND (CASE WHEN home = 'Barcelona' THEN away ELSE home END) IN (SELECT team_name FROM top_clubs)""",
    'season_2015_16': """
        SELECT match_id FROM match_list WHERE season_name = '2015/2016'""",
    'top10_2015_16': """
        SELECT match_id FROM match_list
        WHERE season_name = '2015/2016'
          AND home IN (SELECT team_name FROM top_clubs) AND away IN (SELECT team_name FROM top_clubs)""",
}


def assign_categories(conn):
    conn.execute('DELETE FROM match_categories')
    for name, sql in CATEGORIES.items():
        conn.execute(f'INSERT INTO match_categories SELECT match_id, %s FROM ({sql}) q', (name,))


# Seasons where the open data never names the manager. Tito Vilanova was Barcelona's head coach all of 2012/13
# (Jordi Roura stood in during his treatment, but Vilanova kept the post); the reference pipeline uses the same.
KNOWN_MANAGERS = {('2012/2013', 'Barcelona'): 'Tito Vilanova'}


def fill_missing_managers(conn):
    """Fill an empty manager field when the team had exactly one named manager in that season's loaded matches,
    or from KNOWN_MANAGERS. Teams that changed manager mid-season keep the gap. Returns the number of fields filled."""
    filled = 0
    for side in ('home', 'away'):
        filled += conn.execute(f"""
            WITH named AS (
                SELECT season_name, team_id, min(manager) AS manager
                FROM (SELECT season_name, home_team_id AS team_id, home_manager AS manager FROM matches
                      UNION ALL SELECT season_name, away_team_id, away_manager FROM matches) q
                WHERE manager IS NOT NULL AND manager <> ''
                GROUP BY 1, 2 HAVING count(DISTINCT manager) = 1)
            UPDATE matches m SET {side}_manager = n.manager
            FROM named n
            WHERE n.season_name = m.season_name AND n.team_id = m.{side}_team_id
              AND ({side}_manager IS NULL OR {side}_manager = '')""").rowcount
        for (season, team), manager in KNOWN_MANAGERS.items():
            filled += conn.execute(f"""
                UPDATE matches m SET {side}_manager = %s FROM teams t
                WHERE t.team_id = m.{side}_team_id AND t.team_name = %s AND m.season_name = %s
                  AND ({side}_manager IS NULL OR {side}_manager = '')""", (manager, team, season)).rowcount
    return filled
