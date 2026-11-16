"""Ham veriyi indirme ve okuma. İndirilen her dosya data/raw altında saklanır; varsa tekrar indirilmez."""
import json
import os
import time
import urllib.request

from . import RAW

BASE = 'https://raw.githubusercontent.com/statsbomb/open-data/master/data/'
LA_LIGA = 11
FIRST_SEASON = '2005'


def fetch(path, dest, retries=5, wait=2.0):
    """BASE/path adresini dest dosyasına indirir. Ağ hatasında artan beklemeyle yeniden dener.
    Yarım kalan indirme kalıcı dosyayı bozmasın diye önce geçici dosyaya yazar."""
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
    """2005/06'dan itibaren açık verideki Real Madrid-Barcelona La Liga maçları, tarihe göre sıralı.
    Her maça sezon adı 'season' alanı olarak eklenir."""
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
    """Maçın olayları (uzatma devreleri hariç), dosyadaki sırayla."""
    ev = load_json(f'events/{match_id}.json', f'{match_id}.json', raw)
    return [e for e in ev if e['period'] <= max_period]
