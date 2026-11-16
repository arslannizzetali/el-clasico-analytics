"""Bütün zinciri sırayla çalıştırır: veri indirme + dönüştürme + doğrulama.

    python3 pipeline.py              # data/processed altına yazar
    python3 pipeline.py /tmp/cikti   # başka bir klasöre yazar

İlk çalıştırmada StatsBomb açık verisi data/raw altına indirilir (birkaç dakika); sonra önbellekten okunur.
"""
import os
import subprocess
import sys
import time

ROOT = os.path.dirname(os.path.abspath(__file__))
STEPS = ['build.py', 'losses.py', 'strips.py', 'game_state.py', 'kayiplar.py']


def main():
    out = sys.argv[1:] or []
    t0 = time.time()
    for step in STEPS:
        s = time.time()
        r = subprocess.run([sys.executable, os.path.join(ROOT, 'scripts', step), *out])
        if r.returncode != 0:
            sys.exit(f'{step} başarısız oldu (çıkış kodu {r.returncode})')
        print(f'  ({step} {time.time() - s:.0f} sn)')
    print(f'Tamam: {len(STEPS)} adım, {time.time() - t0:.0f} sn')


if __name__ == '__main__':
    main()
