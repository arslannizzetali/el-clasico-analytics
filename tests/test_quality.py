"""The data quality checks pass on the loaded data and catch defects injected into it.

Each defect is written inside a transaction that is rolled back, so the database is left as it was.
Needs requirements.txt and a loaded database; skipped otherwise."""
import os
import sys
import unittest
import uuid

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    from clasico import db, quality
    with db.connect() as _c:
        READY = _c.execute('SELECT count(*) FROM matches').fetchone()[0] > 0
except Exception:  # psycopg missing or database down
    READY = False
if os.environ.get('REQUIRE_DB') and not READY:
    raise RuntimeError('REQUIRE_DB is set but the database is not loaded')


def failing(conn):
    return {c.name for c, n, ok in quality.run(conn) if not ok}


@unittest.skipUnless(READY, 'needs requirements.txt and a loaded database')
class QualityChecks(unittest.TestCase):
    def setUp(self):
        self.conn = db.connect()
        self.mid = self.conn.execute('SELECT min(match_id) FROM matches').fetchone()[0]

    def tearDown(self):
        self.conn.rollback()
        self.conn.close()

    def test_loaded_data_passes(self):
        bad = {c.name for c, n, ok in quality.run(self.conn) if not ok and c.severity == 'error'}
        self.assertEqual(bad, set())

    def inject(self, sql, *args):
        self.conn.execute(sql, args)
        return failing(self.conn)

    def test_catches_duplicate_on_ball_event(self):
        bad = self.inject("""INSERT INTO events SELECT %s, match_id, 100000, period, minute, second, ts, type, team_id,
                             player_id, possession, possession_team_id, play_pattern, x, y, end_x, end_y, outcome, subtype,
                             xg, duration, under_pressure, raw FROM events WHERE match_id = %s AND type = 'Pass' LIMIT 1""",
                          str(uuid.uuid4()), self.mid)
        self.assertIn('duplicates: no repeated on-ball event', bad)

    def test_catches_missing_location(self):
        bad = self.inject("UPDATE events SET x = NULL WHERE event_id = (SELECT event_id FROM events WHERE match_id = %s AND type = 'Shot' LIMIT 1)", self.mid)
        self.assertIn('nulls: on-ball events have a location', bad)

    def test_catches_missing_lineup(self):
        bad = self.inject("DELETE FROM events WHERE event_id = (SELECT event_id FROM events WHERE match_id = %s AND type = 'Starting XI' LIMIT 1)", self.mid)
        self.assertIn('completeness: two starting line-ups per match', bad)

    def test_catches_score_mismatch(self):
        bad = self.inject('UPDATE matches SET home_score = home_score + 1 WHERE match_id = %s', self.mid)
        self.assertIn('consistency: goals in the events equal the score', bad)

    def test_catches_schema_change(self):
        bad = self.inject('ALTER TABLE events ALTER COLUMN xg TYPE numeric')
        self.assertIn('schema: events has the expected columns and types', bad)


if __name__ == '__main__':
    unittest.main()
