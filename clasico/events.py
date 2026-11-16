"""Olay verisi üzerinde ortak tanımlar. Bütün metrikler bu fonksiyonları kullanır; bir tanım
değişirse her çıktı birlikte değişir."""

LOSS_KIND = {'Dispossessed': 'Kaptırma', 'Miscontrol': 'Kontrol hatası', 'Dribble': 'Başarısız çalım'}
STRIP_WINDOW = 12   # saniye: top kontrolünden sonra kaybın aranacağı süre
STRIP_LOOKAHEAD = 40  # olay: aramanın en fazla kaç olay ileri gideceği


def sec(e):
    """Olayın devre içindeki zamanı, saniye."""
    h, m, s = e['timestamp'].split(':')
    return int(h) * 3600 + int(m) * 60 + float(s)


def is_clean_receipt(e):
    """Başarılı top alışı: Ball Receipt* ve sonucu (Incomplete vb.) yok."""
    return e['type']['name'] == 'Ball Receipt*' and 'outcome' not in e.get('ball_receipt', {})


def is_loss(e):
    """Topu elden çıkaramadan kaybetme: Dispossessed, Miscontrol ya da başarısız çalım."""
    n = e['type']['name']
    return n in ('Dispossessed', 'Miscontrol') or (n == 'Dribble' and e['dribble']['outcome']['name'] == 'Incomplete')


def strip_after(ev, i):
    """ev[i] başarılı bir top alışıysa, aynı oyuncunun topla yaptığı ilk anlamlı aksiyon (top sürme hariç)
    bir kayıpsa o kayıp olayını döndürür, değilse None. Arama aynı devrede ve 12 saniye içinde kalır."""
    e = ev[i]
    team, player, t0 = e['team']['name'], e['player']['id'], sec(e)
    for f in ev[i + 1:i + STRIP_LOOKAHEAD]:
        if f['period'] != e['period'] or sec(f) - t0 > STRIP_WINDOW:
            return None
        if f.get('player', {}).get('id') != player or f['team']['name'] != team:
            continue
        if f['type']['name'] == 'Carry':
            continue
        return f if is_loss(f) else None
    return None


def possessions(ev):
    """Olayları StatsBomb'un atak (possession) numarasına göre devre devre gruplar."""
    seqs = []
    for per in (1, 2):
        cur = None
        for e in ev:
            if e['period'] != per:
                continue
            if cur is None or e['possession'] != cur['p']:
                cur = dict(p=e['possession'], team=e['possession_team']['name'], pp=e['play_pattern']['name'], es=[], per=per)
                seqs.append(cur)
            cur['es'].append(e)
    return seqs


def passes_before(es, shot):
    """Atak içinde, şutu çeken takımın şuttan önce yaptığı isabetli pas sayısı."""
    t = shot['team']['name']
    return sum(1 for e in es if e['type']['name'] == 'Pass' and e['team']['name'] == t
               and e['index'] < shot['index'] and 'outcome' not in e['pass'])


def zone(x, y):
    """Sahayı 3x3 eşit parçaya böler (her biri 40 x 26,7). Takım soldan sağa hücum eder:
    1-2-3 kendi üçte biri, 4-5-6 orta saha, 7-8-9 rakip üçte biri."""
    third = 0 if x < 40 else 1 if x < 80 else 2
    lane = 0 if y < 80 / 3 else 1 if y < 160 / 3 else 2
    return 1 + lane + 3 * third


def is_goal(e):
    return (e['type']['name'] == 'Shot' and e['shot']['outcome']['name'] == 'Goal') or e['type']['name'] == 'Own Goal For'


def score_before(ev, teams):
    """Her olay için o olaydan ÖNCE atılmış goller {takım: gol}. ev olay sırasına (index) göre sıralı olmalı."""
    score = {t: 0 for t in teams}
    out = []
    for e in ev:
        out.append(dict(score))
        if is_goal(e):
            score[e['team']['name']] += 1
    return out, score


def game_state(score, team, opp):
    d = score[team] - score[opp]
    return 'Önde' if d > 0 else 'Geride' if d < 0 else 'Berabere'
