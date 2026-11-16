"""Step 5: loss_table.csv, one row per ball lost after a controlled touch, for spreadsheet use.

Joins losses_ds.json (result, xG, location) with strips.json (players pressing). Both are produced by the
same event loop, so rows are in the same order; the script stops if they are not.
Zone and x/y are where the ball was lost, from the losing team's view.
Input: losses_ds.json (losses.py), strips.json (strips.py).
"""
import csv
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from clasico import PROCESSED  # noqa: E402
from clasico.events import zone  # noqa: E402
from clasico.output import read_json, read_rows  # noqa: E402

OUT = sys.argv[1] if len(sys.argv) > 1 else PROCESSED
HEADER = ['match', 'minute', 'losing_team', 'player', 'loss_kind', 'zone', 'result', 'opponent_shot_xg',
          'players_pressing', 'period', 'x', 'y']


def main():
    L = read_rows(os.path.join(OUT, 'losses_ds.json'))
    S = read_json(os.path.join(OUT, 'strips.json'))
    assert len(L) == len(S), f'row counts differ: losses {len(L)}, strips {len(S)}'
    for l, s in zip(L, S):
        assert (l['match'], l['team'], l['player'], l['kind']) == (s['match'], s['losing_team'], s['player'], s['loss_kind']), f"order broken at loss_id {l['loss_id']}"
    with open(os.path.join(OUT, 'loss_table.csv'), 'w', newline='') as fh:
        w = csv.writer(fh)
        w.writerow(HEADER)
        for l, s in zip(L, S):
            w.writerow([l['match'], l['minute'], l['team'], l['player'], l['kind'], zone(l['x'], l['y']), l['result'], l['xg'],
                        s['pressers'], l['period'], l['x'], l['y']])
    print(f'loss_table: {len(L)} rows')


if __name__ == '__main__':
    main()
