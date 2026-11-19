"""Download the event and lineup files of every La Liga match into the raw cache (parallel, resumable).

    python3 scripts/download.py            # all La Liga seasons 2004/05-2020/21 (~866 matches, a few GB)
    python3 scripts/download.py clasico    # only the Real Madrid - Barcelona matches
"""
import os
import sys
from concurrent.futures import ThreadPoolExecutor

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from clasico import RAW, data  # noqa: E402


def main():
    scope = sys.argv[1] if len(sys.argv) > 1 else 'all'
    ms = data.scope_matches(scope)
    jobs = [(f"events/{g['match_id']}.json", f"{g['match_id']}.json") for g in ms]
    jobs += [(f"lineups/{g['match_id']}.json", f"lineups_{g['match_id']}.json") for g in ms]
    todo = [j for j in jobs if not os.path.exists(os.path.join(RAW, j[1]))]
    print(f'{len(ms)} matches, {len(todo)} of {len(jobs)} files to download into {RAW}')
    with ThreadPoolExecutor(8) as pool:
        for k, _ in enumerate(pool.map(lambda j: data.fetch(j[0], os.path.join(RAW, j[1])), todo), 1):
            if k % 100 == 0 or k == len(todo):
                print(f'  {k}/{len(todo)}', flush=True)


if __name__ == '__main__':
    main()
