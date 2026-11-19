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
sys.path.insert(0, ROOT)
from clasico.log import get_logger  # noqa: E402

log = get_logger('pipeline')
STEPS = ['build.py', 'losses.py', 'strips.py', 'game_state.py', 'uncertainty.py', 'loss_table.py']


def main():
    out = sys.argv[1:] or []
    t0 = time.time()
    for step in STEPS:
        s = time.time()
        r = subprocess.run([sys.executable, os.path.join(ROOT, 'scripts', step), *out])
        if r.returncode != 0:
            log.error('step failed', extra={'step': step, 'exit_code': r.returncode})
            sys.exit(1)
        log.info('step done', extra={'step': step, 'seconds': round(time.time() - s, 1)})
    log.info('pipeline done', extra={'steps': len(STEPS), 'seconds': round(time.time() - t0, 1)})


if __name__ == '__main__':
    main()
