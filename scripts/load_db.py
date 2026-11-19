"""Load StatsBomb La Liga matches into PostgreSQL (schema: db/schema.sql).

    docker compose up -d
    python3 scripts/load_db.py             # every La Liga match 2004/05-2020/21
    python3 scripts/load_db.py clasico     # only the Clásicos (what CI loads)
    python3 scripts/load_db.py --reload    # replace matches that are already loaded

Missing raw files are downloaded on the way (scripts/download.py does it faster, in parallel).
"""
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from clasico import data, db  # noqa: E402


def main():
    args = sys.argv[1:]
    reload = '--reload' in args
    scope = next((a for a in args if not a.startswith('--')), 'all')
    ms = data.scope_matches(scope)
    t0 = time.time()
    with db.connect() as conn:
        db.apply_schema(conn)
        conn.commit()
        have = {r[0] for r in conn.execute('SELECT match_id FROM matches')}
        todo = [g for g in ms if reload or g['match_id'] not in have]
        print(f'{len(ms)} matches in scope, {len(todo)} to load')
        for k, g in enumerate(todo, 1):
            db.load_match(conn, g, data.load_json(f"events/{g['match_id']}.json", f"{g['match_id']}.json"),
                          data.lineups(g['match_id']))
            conn.commit()
            if k % 50 == 0 or k == len(todo):
                print(f'  {k}/{len(todo)}  ({time.time() - t0:.0f} s)', flush=True)
        print(f'  managers filled where the season names only one: {db.fill_missing_managers(conn)}')
        db.load_standings(conn)
        db.assign_categories(conn)
        conn.commit()
        for cat, n in conn.execute('SELECT category, count(*) FROM match_categories GROUP BY 1 ORDER BY 1'):
            print(f'  {cat}: {n} matches')
        n_m, n_e = conn.execute('SELECT (SELECT count(*) FROM matches), (SELECT count(*) FROM events)').fetchone()
    print(f'load_db: {n_m} matches, {n_e} events in the database')


if __name__ == '__main__':
    main()
