"""5. adım: kayiplar.csv — claude.ai tablosu için kaptırılan toplar listesi.

losses_ds.json (sonuç, xG, konum) ile strips.json'u (baskıya giden rakip sayısı) birleştirir.
İki dosya aynı olay döngüsüyle üretildiği için satırlar aynı sırada; sıra bozulursa script durur.
Bölge ve x/y topu kaptıran takımın gözünden, kaybın olduğu nokta.
Girdi: losses_ds.json (losses.py), strips.json (strips.py).
"""
import csv
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from clasico import PROCESSED  # noqa: E402
from clasico.events import zone  # noqa: E402
from clasico.output import read_json, read_rows  # noqa: E402

OUT = sys.argv[1] if len(sys.argv) > 1 else PROCESSED
HEADER = ['Maç', 'Dakika', 'Topu kaptıran takım', 'Topu kaptıran oyuncu', 'Kayıp türü', 'Bölge', 'Sonuç', 'Rakip şutunun xG',
          'Baskıya giden rakip', 'Dönem', 'x', 'y']


def main():
    L = read_rows(os.path.join(OUT, 'losses_ds.json'))
    S = read_json(os.path.join(OUT, 'strips.json'))
    assert len(L) == len(S), f'satır sayısı tutmuyor: losses {len(L)}, strips {len(S)}'
    for l, s in zip(L, S):
        assert (l['match'], l['team'], l['player'], l['kind']) == (s['mac'], s['topu_kaptiran_takim'], s['oyuncu'], s['kayip_turu']), f"sıra bozuk: loss_id {l['loss_id']}"
    with open(os.path.join(OUT, 'kayiplar.csv'), 'w', newline='') as fh:
        w = csv.writer(fh)
        w.writerow(HEADER)
        for l, s in zip(L, S):
            w.writerow([l['match'], l['minute'], l['team'], l['player'], l['kind'], zone(l['x'], l['y']), l['result'], l['xg'],
                        s['baskiya_giden'], l['period'], l['x'], l['y']])
    print(f'kayiplar: {len(L)} satır')


if __name__ == '__main__':
    main()
