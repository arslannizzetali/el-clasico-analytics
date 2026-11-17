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
    losses = read_rows(os.path.join(OUT, 'losses_ds.json'))
    strips = read_json(os.path.join(OUT, 'strips.json'))
    assert len(losses) == len(strips), f'row counts differ: losses {len(losses)}, strips {len(strips)}'
    for loss, strip in zip(losses, strips):
        same = ((loss['match'], loss['team'], loss['player'], loss['kind'])
                == (strip['match'], strip['losing_team'], strip['player'], strip['loss_kind']))
        assert same, f"order broken at loss_id {loss['loss_id']}"
    with open(os.path.join(OUT, 'loss_table.csv'), 'w', newline='') as fh:
        writer = csv.writer(fh)
        writer.writerow(HEADER)
        for loss, strip in zip(losses, strips):
            writer.writerow([loss['match'], loss['minute'], loss['team'], loss['player'], loss['kind'],
                             zone(loss['x'], loss['y']), loss['result'], loss['xg'],
                             strip['pressers'], loss['period'], loss['x'], loss['y']])
    print(f'loss_table: {len(losses)} rows')


if __name__ == '__main__':
    main()
