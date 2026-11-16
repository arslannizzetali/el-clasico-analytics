"""Runs the whole chain in order: download, transform, validate.

    python3 pipeline.py              # writes to data/processed
    python3 pipeline.py /tmp/out     # writes to another folder

The first run downloads the StatsBomb open data to data/raw (a few minutes); later runs read the cache.
"""
import os
import subprocess
import sys
import time

ROOT = os.path.dirname(os.path.abspath(__file__))
STEPS = ['build.py', 'losses.py', 'strips.py', 'game_state.py', 'uncertainty.py', 'loss_table.py']


def main():
    out = sys.argv[1:] or []
    t0 = time.time()
    for step in STEPS:
        s = time.time()
        r = subprocess.run([sys.executable, os.path.join(ROOT, 'scripts', step), *out])
        if r.returncode != 0:
            sys.exit(f'{step} failed (exit code {r.returncode})')
        print(f'  ({step} {time.time() - s:.0f} s)')
    print(f'Done: {len(STEPS)} steps, {time.time() - t0:.0f} s')


if __name__ == '__main__':
    main()
