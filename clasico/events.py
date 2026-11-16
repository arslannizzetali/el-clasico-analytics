"""Shared definitions on event data. Every metric uses these functions, so changing a definition here
changes every output together."""

LOSS_KIND = {'Dispossessed': 'Dispossessed', 'Miscontrol': 'Miscontrol', 'Dribble': 'Failed dribble'}
STRIP_WINDOW = 12     # seconds after a ball receipt in which a loss is looked for
STRIP_LOOKAHEAD = 40  # maximum number of events scanned ahead
STATES = ('Ahead', 'Level', 'Behind')


def sec(e):
    """Event time within its half, in seconds."""
    h, m, s = e['timestamp'].split(':')
    return int(h) * 3600 + int(m) * 60 + float(s)


def is_clean_receipt(e):
    """A successful ball receipt: Ball Receipt* without an outcome (such as Incomplete)."""
    return e['type']['name'] == 'Ball Receipt*' and 'outcome' not in e.get('ball_receipt', {})


def is_loss(e):
    """Losing the ball before releasing it: Dispossessed, Miscontrol or a failed dribble."""
    n = e['type']['name']
    return n in ('Dispossessed', 'Miscontrol') or (n == 'Dribble' and e['dribble']['outcome']['name'] == 'Incomplete')


def strip_after(ev, i):
    """If ev[i] is a successful receipt, return the loss event when the same player's first meaningful
    action with the ball (carries skipped) is a loss; otherwise None. Search stays in the same half
    and within 12 seconds."""
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
    """Group events by StatsBomb possession number, half by half."""
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
    """Completed passes by the shooting team within the possession before the shot."""
    t = shot['team']['name']
    return sum(1 for e in es if e['type']['name'] == 'Pass' and e['team']['name'] == t
               and e['index'] < shot['index'] and 'outcome' not in e['pass'])


def zone(x, y):
    """Split the pitch into 3 x 3 equal zones (40 x 26.7 each), team attacking left to right:
    1-3 own third, 4-6 middle third, 7-9 attacking third."""
    third = 0 if x < 40 else 1 if x < 80 else 2
    lane = 0 if y < 80 / 3 else 1 if y < 160 / 3 else 2
    return 1 + lane + 3 * third


def is_goal(e):
    return (e['type']['name'] == 'Shot' and e['shot']['outcome']['name'] == 'Goal') or e['type']['name'] == 'Own Goal For'


def score_before(ev, teams):
    """For every event, the goals scored BEFORE it {team: goals}. ev must be sorted by index."""
    score = {t: 0 for t in teams}
    out = []
    for e in ev:
        out.append(dict(score))
        if is_goal(e):
            score[e['team']['name']] += 1
    return out, score


def game_state(score, team, opp):
    d = score[team] - score[opp]
    return 'Ahead' if d > 0 else 'Behind' if d < 0 else 'Level'
