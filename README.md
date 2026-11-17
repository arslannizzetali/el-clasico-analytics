# El Clásico, 2005–2021: how the game changed

[![CI](https://github.com/arslannizzetali/el-clasico-analytics/actions/workflows/ci.yml/badge.svg)](https://github.com/arslannizzetali/el-clasico-analytics/actions/workflows/ci.yml)

A match-by-match tactical analysis of **29 Real Madrid – Barcelona La Liga matches** (November 2005 – April 2021),
built from StatsBomb's free event data. The goal is evidence rather than narrative: every number traces back to
individual events, matches and pitch locations, and every claim comes with how sure we can be about it.

**[Open the interactive dashboard →](https://arslannizzetali.github.io/el-clasico-analytics/)**

Data: [StatsBomb Open Data](https://github.com/statsbomb/open-data). These matches are in the open data because
StatsBomb released Lionel Messi's full Barcelona career, so coverage follows Barcelona's league Clásicos.

## Key findings

| | 2005-09 | 2009-13 | 2013-17 | 2017-21 | Change [90% interval] |
|---|---|---|---|---|---|
| Barcelona: passes before an open-play shot | 5.0 | **11.1** | 8.8 | 7.0 | 2009-13 → 2017-21: −4.1 [−7.8, −0.7] |
| Real Madrid: passes before an open-play shot | **4.1** | 4.1 | 5.6 | **7.2** | 2005-09 → 2017-21: +3.1 [+1.6, +4.4] |
| Barcelona: PPDA (higher = less pressure) | 10.0 | **9.5** | 12.0 | **17.9** | 2009-13 → 2017-21: +8.4 [+6.0, +11.1] |
| Barcelona: balls stripped per 100 opponent controls | 8.6 | **10.1** | 6.3 | **5.0** | 2009-13 → 2017-21: −5.1 [−6.8, −3.5] |
| Real Madrid: press success (%) | 16.8 | **13.6** | 18.7 | **21.4** | 2009-13 → 2017-21: +7.8 [+4.6, +11.3] pts |

**1. The two styles converged.** By period, Barcelona's build-up peaked in 2009-13 (11.1 passes before a shot) and
fell to 7; Real Madrid went from direct play (4) to 7. Both changes hold under resampling. The 2009-13 peak is **not**
a Guardiola peak, though: grouped by coach (below), Guardiola's Clásicos average 8.9 passes, the same as Luis
Enrique's 8.7, and the period figure is lifted by Vilanova's two matches (13.9).

### By Barcelona coach

The four-season periods do not follow coaching changes: Guardiola's first two Clásicos (2008-12-13, 2009-05-02) fall in
2005-09 and Vilanova's two in 2009-13. The dashboard can therefore group the same matches by Barcelona's coach on
the day (Real Madrid's numbers are grouped the same way, so both teams can be compared within a Barcelona coach).

| Barcelona | Rijkaard (4) | Guardiola (8) | Vilanova (2) | Martino (2) | Luis Enrique (6) | Valverde (4) | Setién (1) | Koeman (2) |
|---|---|---|---|---|---|---|---|---|
| Passes before an open-play shot | 4.8 | 8.9 | *13.9* | *9.3* | 8.7 | 7.4 | *7.6* | *6.1* |
| PPDA (higher = less pressure) | 10.3 | **9.6** | *9.3* | *10.9* | 12.4 | 20.4 | *13.8* | *16.2* |
| Balls stripped per 100 opponent controls | 7.4 | **10.8** | *9.2* | *6.9* | 6.2 | 4.9 | *5.4* | *5.1* |
| Press success (%) | 19.8 | **30.5** | *26.9* | *24.5* | 20.9 | 19.0 | *17.6* | *25.5* |

Matches in brackets. *Italics*: fewer than 4 matches, shown but given no interval and left out of every comparison.

**How small coaches are handled.** A coach needs at least 4 Clásicos to get a bootstrap interval and to enter the
change tests; that leaves Rijkaard, Guardiola, Luis Enrique and Valverde. With one or two matches a resample can only
repeat those same matches, so the "interval" would just be the spread of two numbers, and Setién's single match has no
spread at all. They are not merged into a neighbour either: Vilanova with Guardiola, say, would be defensible on
continuity but would quietly decide the very question the grouping is meant to test. Their averages are shown,
marked, and left out of claims.

**What survives the regrouping.** Guardiola's Barcelona pressed hardest against Real Madrid on every pressing measure:
press success 30.5% against 20.9% under Luis Enrique (change −9.6 [−12.7, −6.5] points) and 19.0% under Valverde;
balls stripped 10.8 per 100 against 6.2 and 4.9; PPDA 9.6 against 12.4 and 20.4. The build-up claim does not
survive: Guardiola 8.9 [6.3, 11.6] against Luis Enrique 8.7 [7.6, 9.9], change −0.2 [−3.2, +2.6]. What the coach
view does show is that Barcelona's build-up lengthened after Rijkaard (4.8 → 8.9, change +4.1 [+1.1, +7.0]).

![The two styles converged](docs/img/convergence.svg)

**2. Barcelona's press faded, and the scoreline does not explain it.** With the score level, PPDA went from 8.4
(2009-13) to 19.9 (2017-21), change +11.4 [+8.0, +15.9]. In 2017-21 Barcelona led for only 20% of the minutes,
so "they sat back while winning" is not the reason. Press success and balls stripped fell the same way. Real Madrid's
press, meanwhile, became more effective.

![Barcelona's press faded regardless of the score](docs/img/press.svg)

**3. Losing the ball in midfield is what hurts.** Barcelona's central-midfield losses (zone 5) end in an opponent shot
12.5% of the time, against 1–4% in the attacking third, although most of those shots come from distance. Only 1 of
Barcelona's 744 losses after a controlled touch led to a goal within 20 seconds; Real Madrid's led to 5.

![Where losing the ball costs a shot](docs/img/zones.svg)

### How sure are these numbers?

Each period average rests on only 6–8 matches (each coach average on 4–8), so every average in the dashboard carries a **90% bootstrap
interval**: the period's matches are resampled with replacement 5,000 times and the metric is recomputed from the
resampled totals. The match is the unit of resampling because events within a match are not independent. A change
between periods is called clear only when its interval excludes zero; 56 of the 108 period-to-period changes are.
Example of one that is not: Real Madrid's PPDA with the score level, 2005-09 → 2017-21, +0.4 [−2.7, +3.2].

## Interactive dashboard

The [dashboard](https://arslannizzetali.github.io/el-clasico-analytics/) is a single static file
([`docs/index.html`](docs/index.html)): pick a team and a metric, see every match as a point and every period as an
average with its interval, split pressing and build-up metrics by score state, click a pitch zone to list the losses
behind it, and open a match report with both teams against their period average. Light and dark mode, works on a phone.

It runs exactly the same page code as the working dashboard; `site/build_site.py` embeds the processed data and a
small stand-in for the dashboard API, so the two versions cannot drift apart.

## How the metrics are measured

| Metric | Definition |
|---|---|
| Passes before a shot | Completed passes by the shooting team in the possession before its **first** open-play shot (penalties, corners and free kicks excluded). Later shots in the same possession are listed but not counted, so passes are not double-counted. |
| Quick shot after turnover | Share of open-play turnovers followed by an opponent shot within 15 s. |
| Regain within 8 s | Share of turnovers won back within 8 s. |
| Press success | Share of a team's pressures followed by its own possession within 5 s. |
| PPDA | Opponent passes in their own build-up zone (x ≤ 72) per defensive action (tackle, interception, foul) at x ≥ 48. |
| Ball stripped | A player completes a ball receipt and loses it before releasing it (Dispossessed, Miscontrol or failed dribble, within 12 s), per 100 opponent controls. |
| Players pressing | Distinct opponents with a pressure event within ~11 m of the ball between receipt and loss. Off-ball positions are not in event data, so this is a lower bound. |
| Game state | Every event is labelled Ahead / Level / Behind from goals scored *before* it (penalties and own goals included). Metrics are re-aggregated by state; the three states always sum to the match totals. |
| Pitch zones | 9 equal zones (3 × 3, 40 × 26.7 units) from the view of the team losing the ball, attacking left to right: 1-3 own third, 4-6 middle third, 7-9 attacking third. |

## Project layout

```
clasico/            shared definitions (one place for every rule)
  data.py           download with retries + local cache (data/raw)
  events.py         time, ball-strip detection, possessions, zones, game state
  output.py         JSON/CSV writing; each JSON carries the code that produced it
scripts/            pipeline steps, run in this order by pipeline.py
  build.py          match-team metrics + every non-penalty shot
  losses.py         every ball lost after a controlled touch, with the opponent shot that followed
  strips.py         players pressing each loss
  game_state.py     main metrics split by Ahead / Level / Behind
  uncertainty.py    bootstrap intervals for period averages and period-to-period changes
  loss_table.py     flat loss table (CSV) for spreadsheet use
site/               build_site.py (static dashboard -> docs/index.html), readme_charts.py (docs/img/*.svg)
docs/               published site: index.html + README charts
tests/              unit tests on hand-built events + consistency tests on outputs
data/processed/     outputs (data/raw is downloaded and not committed)
dashboard/          dashboard page source
.github/workflows/  CI: tests, freshness of generated files, full rebuild from raw data
```

## Run it

Python 3.10+ and the standard library only; nothing to install.

```bash
python3 pipeline.py                      # downloads the data on first run, then ~40 s
python3 -m unittest discover -s tests    # 21 tests
python3 site/build_site.py               # rebuild docs/index.html
python3 site/readme_charts.py            # rebuild the README charts
```

The tests check the definitions on small synthetic event sequences (what counts as a strip, how the score state is
assigned around a goal, zone edges) and the outputs against each other: 29 matches, mirrored scores, game-state
splits summing to match totals, loss and strip tables lining up row by row, intervals containing their estimates.

CI runs on every push: the tests; a check that the site and charts are up to date with the data; and a full rebuild
from raw StatsBomb data that must reproduce every committed output byte for byte (the bootstrap uses a fixed seed).

## Credits

Event data © StatsBomb, released as open data under their
[user agreement](https://github.com/statsbomb/open-data/blob/master/LICENSE.pdf).
