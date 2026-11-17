"""Download and read the raw data. Every downloaded file is cached under data/raw and never fetched twice."""
import json
import os
import time
import urllib.request

from . import RAW

# The open data are read from one fixed commit of github.com/statsbomb/open-data, not from master, so a later
# correction by StatsBomb cannot silently change the outputs. To update: set this to a newer commit, delete
# data/raw, run pipeline.py and commit the regenerated data/processed (the CI cache key follows this value).
STATSBOMB_SHA = '4b73468fc5b0f1950f9f66fada70ad3a4f9327cb'   # master on 2026-09-07
BASE = f'https://raw.githubusercontent.com/statsbomb/open-data/{STATSBOMB_SHA}/data/'
LA_LIGA = 11
FIRST_SEASON = '2005'


def fetch(path, dest, retries=5, wait=2.0):
    """Download BASE/path to dest, retrying network errors with a growing wait.
    Writes to a temporary file first so an interrupted download never leaves a broken cache file."""
    if os.path.exists(dest):
        return dest
    os.makedirs(os.path.dirname(dest), exist_ok=True)
    tmp = dest + '.part'
    for attempt in range(1, retries + 1):
        try:
            with urllib.request.urlopen(BASE + path, timeout=60) as r, open(tmp, 'wb') as fh:
                fh.write(r.read())
            os.replace(tmp, dest)
            return dest
        except OSError:
            if os.path.exists(tmp):
                os.remove(tmp)
            if attempt == retries:
                raise
            time.sleep(wait * attempt)


def load_json(path, dest_name, raw=RAW):
    with open(fetch(path, os.path.join(raw, dest_name)), encoding='utf-8') as fh:
        return json.load(fh)


def clasico_matches(raw=RAW):
    """Real Madrid - Barcelona La Liga matches in the open data from 2005/06 on, sorted by date.
    The season name is added to each match as 'season'."""
    comps = load_json('competitions.json', 'c.json', raw)
    out = []
    for c in comps:
        if c['competition_id'] == LA_LIGA and c['season_name'] >= FIRST_SEASON:
            for g in load_json(f"matches/{LA_LIGA}/{c['season_id']}.json", f"matches_{LA_LIGA}_{c['season_id']}.json", raw):
                if {g['home_team']['home_team_name'], g['away_team']['away_team_name']} == {'Real Madrid', 'Barcelona'}:
                    g['season'] = c['season_name']
                    out.append(g)
    return sorted(out, key=lambda g: g['match_date'])


def events(match_id, raw=RAW, max_period=2):
    """A match's events in file order, extra time excluded."""
    ev = load_json(f'events/{match_id}.json', f'{match_id}.json', raw)
    return [e for e in ev if e['period'] <= max_period]
