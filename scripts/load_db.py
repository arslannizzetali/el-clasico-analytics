"""Load StatsBomb matches into PostgreSQL (schema: db/schema.sql).

    docker compose up -d
    python3 scripts/load_db.py             # every La Liga match 2004/05-2020/21 + the Champions League finals
    python3 scripts/load_db.py clasico     # only the Clásicos (CI loads these and the finals)
    python3 scripts/load_db.py ucl_finals  # only Barcelona's and Real Madrid's Champions League finals
    python3 scripts/load_db.py --reload    # replace matches that are already loaded

Idempotent and incremental: a match is written in one transaction (delete, then insert), so a run that stops halfway
leaves every match either fully loaded or absent; a second run loads only the matches that are missing, and running
the same command twice leaves the database unchanged (tests/test_load_db.py). Standings, manager gaps and
categories are recomputed from scratch on every run. Missing raw files are downloaded on the way
(scripts/download.py does it faster, in parallel).
"""
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from clasico import data, db  # noqa: E402
from clasico.log import get_logger  # noqa: E402

log = get_logger('load_db')


def load(scope='all', reload=False):
    """Load one scope; returns {'in_scope', 'loaded', 'matches', 'events'}."""
    ms = data.scope_matches(scope)
    t0 = time.time()
    with db.connect() as conn:
        db.apply_schema(conn)
        conn.commit()
        have = {r[0] for r in conn.execute('SELECT match_id FROM matches')}
        todo = [g for g in ms if reload or g['match_id'] not in have]
        log.info('scope resolved', extra={'scope': scope, 'in_scope': len(ms), 'to_load': len(todo), 'reload': reload})
        for k, g in enumerate(todo, 1):
            ev = data.load_json(f"events/{g['match_id']}.json", f"{g['match_id']}.json")
            db.load_match(conn, g, ev, data.lineups(g['match_id']))
            conn.commit()
            log.debug('match loaded', extra={'match_id': g['match_id'], 'events': len(ev)})
            if k % 50 == 0 or k == len(todo):
                log.info('progress', extra={'loaded': k, 'of': len(todo), 'seconds': round(time.time() - t0, 1)})
        filled = db.fill_missing_managers(conn)
        db.load_standings(conn)
        db.assign_categories(conn)
        conn.commit()
        log.info('derived tables rebuilt', extra={'managers_filled': filled})
        for cat, n in conn.execute('SELECT category, count(*) FROM match_categories GROUP BY 1 ORDER BY 1'):
            log.info('category', extra={'category': cat, 'matches': n})
        n_m, n_e = conn.execute('SELECT (SELECT count(*) FROM matches), (SELECT count(*) FROM events)').fetchone()
    log.info('load done', extra={'matches': n_m, 'events': n_e, 'seconds': round(time.time() - t0, 1)})
    return {'in_scope': len(ms), 'loaded': len(todo), 'matches': n_m, 'events': n_e}


def main():
    args = sys.argv[1:]
    load(next((a for a in args if not a.startswith('--')), 'all'), reload='--reload' in args)


if __name__ == '__main__':
    main()
