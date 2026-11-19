"""Data quality checks on the PostgreSQL event store. Each check is one SQL query returning a number of offending
rows (0 = pass). `error` checks fail the run; `warn` checks only log, for known quirks of the source data.

Thresholds come from profiling the loaded data (873 matches, November 2026): 2,614-4,806 events per match,
no on-ball event without a location, locations at most 0.9 units beyond the lines, every score reproduced from the events, and 3 content-duplicate events in
the source (two Tactical Shift pairs and one Goal Keeper pair with distinct StatsBomb ids), none of them on-ball
actions.
"""
from dataclasses import dataclass

EVENTS_PER_MATCH = (2000, 6000)
ON_BALL = ('Pass', 'Shot', 'Carry', 'Ball Receipt*', 'Pressure', 'Duel', 'Dribble', 'Interception',
           'Dispossessed', 'Miscontrol', 'Clearance', 'Block', 'Ball Recovery', 'Foul Committed')
MAX_SOURCE_DUPLICATES = 5

# column -> data type, for the columns the metrics read (information_schema spelling)
SCHEMA = {
    'events': {'event_id': 'uuid', 'match_id': 'integer', 'idx': 'integer', 'period': 'integer', 'minute': 'integer',
               'ts': 'double precision', 'type': 'text', 'team_id': 'integer', 'player_id': 'integer',
               'possession': 'integer', 'possession_team_id': 'integer', 'play_pattern': 'text',
               'x': 'double precision', 'y': 'double precision', 'end_x': 'double precision', 'outcome': 'text',
               'subtype': 'text', 'xg': 'double precision', 'raw': 'jsonb'},
    'matches': {'match_id': 'integer', 'competition_id': 'integer', 'season_name': 'text', 'match_date': 'date',
                'home_team_id': 'integer', 'away_team_id': 'integer', 'home_score': 'integer', 'away_score': 'integer'},
}


@dataclass
class Check:
    name: str
    severity: str   # 'error' or 'warn'
    sql: str        # returns one integer: offending rows
    limit: int = 0  # pass while the count is <= limit


def schema_checks():
    out = []
    for table, cols in SCHEMA.items():
        expected = ', '.join(f"('{c}', '{t}')" for c, t in cols.items())
        out.append(Check(f'schema: {table} has the expected columns and types', 'error', f"""
            SELECT count(*) FROM (VALUES {expected}) AS e(column_name, data_type)
            WHERE NOT EXISTS (SELECT 1 FROM information_schema.columns c
                              WHERE c.table_name = '{table}' AND c.column_name = e.column_name
                                AND c.data_type = e.data_type)"""))
    return out


ON_BALL_SQL = ', '.join(f"'{t}'" for t in ON_BALL)
CHECKS = schema_checks() + [
    Check('nulls: key event fields', 'error', """
        SELECT count(*) FROM events WHERE match_id IS NULL OR idx IS NULL OR period IS NULL OR ts IS NULL
           OR type IS NULL OR team_id IS NULL OR possession_team_id IS NULL OR play_pattern IS NULL"""),
    Check('nulls: on-ball events have a location', 'error', f"""
        SELECT count(*) FROM events WHERE type IN ({ON_BALL_SQL}) AND (x IS NULL OR y IS NULL)"""),
    Check('nulls: shots have xG', 'error', "SELECT count(*) FROM events WHERE type = 'Shot' AND xg IS NULL"),
    # StatsBomb records balls going out of play just beyond the line (up to 120.9 / 80.8 in this data): allow 1 unit
    Check('range: locations on the 120 x 80 pitch (1 unit beyond the lines allowed)', 'error', """
        SELECT count(*) FROM events WHERE x < -1 OR x > 121 OR y < -1 OR y > 81"""),
    Check('range: time within a period is 0-60 minutes', 'error', """
        SELECT count(*) FROM events WHERE ts < 0 OR ts > 3600"""),
    Check('duplicates: event order (match_id, idx) unique', 'error', """
        SELECT count(*) FROM (SELECT 1 FROM events GROUP BY match_id, idx HAVING count(*) > 1) q"""),
    Check('duplicates: no repeated on-ball event', 'error', f"""
        SELECT count(*) FROM (SELECT 1 FROM events WHERE type IN ({ON_BALL_SQL})
                              GROUP BY match_id, team_id, player_id, type, period, ts, x, y HAVING count(*) > 1) q"""),
    Check('duplicates: repeated events of other types (source quirks)', 'warn', """
        SELECT count(*) FROM (SELECT 1 FROM events GROUP BY match_id, team_id, player_id, type, period, ts, x, y
                              HAVING count(*) > 1) q""", MAX_SOURCE_DUPLICATES),
    Check(f'volume: {EVENTS_PER_MATCH[0]}-{EVENTS_PER_MATCH[1]} events per match', 'error', f"""
        SELECT count(*) FROM matches m
        WHERE (SELECT count(*) FROM events e WHERE e.match_id = m.match_id) NOT BETWEEN {EVENTS_PER_MATCH[0]} AND {EVENTS_PER_MATCH[1]}"""),
    Check('completeness: two starting line-ups per match', 'error', """
        SELECT count(*) FROM matches m
        WHERE (SELECT count(*) FROM events e WHERE e.match_id = m.match_id AND e.type = 'Starting XI') <> 2"""),
    Check('completeness: both halves present', 'error', """
        SELECT count(*) FROM matches m
        WHERE (SELECT count(DISTINCT period) FROM events e WHERE e.match_id = m.match_id AND e.period IN (1, 2)) <> 2"""),
    Check('consistency: goals in the events equal the score', 'error', """
        SELECT count(*) FROM matches m
        WHERE m.home_score + m.away_score <> (SELECT count(*) FROM events e WHERE e.match_id = m.match_id AND e.period <= 4
              AND ((e.type = 'Shot' AND e.outcome = 'Goal') OR e.type = 'Own Goal For'))"""),
    Check('relationships: every event belongs to a loaded match and team', 'error', """
        SELECT count(*) FROM events e
        WHERE NOT EXISTS (SELECT 1 FROM matches m WHERE m.match_id = e.match_id)
           OR NOT EXISTS (SELECT 1 FROM teams t WHERE t.team_id = e.team_id)"""),
    Check('relationships: every match has a category', 'warn', """
        SELECT count(*) FROM matches m WHERE NOT EXISTS (SELECT 1 FROM match_categories c WHERE c.match_id = m.match_id)"""),
]


def run(conn):
    """[(check, count, passed)] for every check. A check whose query cannot run (a column is missing, say) fails
    with count None; each check runs in its own savepoint, so one broken query does not stop the others."""
    import psycopg
    out = []
    for c in CHECKS:
        try:
            with conn.transaction():
                n = conn.execute(c.sql).fetchone()[0]
        except psycopg.Error:
            out.append((c, None, False))
            continue
        out.append((c, n, n <= c.limit))
    return out
