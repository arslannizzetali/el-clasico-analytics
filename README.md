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

**1. The two styles converged.** Barcelona's build-up peaked under Guardiola (11 passes before a shot) and fell to 7;
Real Madrid went from direct play (4) to 7. Both changes hold under resampling.

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

Each period average rests on only 6–8 matches, so every average in the dashboard carries a **90% bootstrap
interval**: the period's matches are resampled with replacement 5,000 times and the metric is recomputed from the
resampled totals. The match is the unit of resampling because events within a match are not independent. A change
between periods is called clear only when its interval excludes zero; 56 of the 108 period-to-period changes are.
Example of one that is not: Real Madrid's PPDA with the score level, 2005-09 → 2017-21, +0.4 [−2.7, +3.2].

## Interactive dashboard

The [dashboard](https://arslannizzetali.github.io/el-clasico-analytics/) is a single static file
([`docs/index.html`](docs/index.html)) with four tabs:

- **El Clásico**: pick a team and a metric, see every match as a point and every period as an average with its
  interval, split pressing and build-up metrics by score state, click a pitch zone to list the losses behind it, and
  open a match report with both teams against their period average.
- **League context**: the Clásico against Barcelona's other league matches, with the differences and their
  intervals; any group of matches (Clásicos, Barcelona against top-10 clubs, all Barcelona matches, any club in
  2015/16) match by match; an opponent explorer ranking clubs by how hard they made it for the team, down to the
  formations and tactical shifts of each match; and how opponents lined up, period by period.
- **UCL finals**: Barcelona's three and Real Madrid's four Champions League finals, each set against the team's
  own single matches that season, metric by metric, with the formations during the final.
- **Special seasons**: a new coach's first season. Barcelona under Rijkaard (2007/08) and Guardiola (2008/09),
  Real Madrid under Benítez and Zidane (2015/16), every metric before and after with a 90% interval.

Light and dark mode, works on a phone. It runs exactly the same page code as the working dashboard
([`dashboard/index.html`](dashboard/index.html) and [`dashboard/league.html`](dashboard/league.html));
`site/build_site.py` embeds the processed data and a small stand-in for the dashboard API, so the two versions
cannot drift apart.

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

## League-wide data: PostgreSQL + pandas

The Clásico analysis above runs on the standard library alone and stays the reference. Next to it, every La Liga
match in the open data goes into a PostgreSQL event store, and the same metrics are computed with pandas on any
group of matches. Tests check that both give identical numbers on the Clásicos and on the Champions League finals (other
opponents, extra time), and CI runs them against a real PostgreSQL service.

What the open data covers decides what can be compared: Barcelona's league matches 2004/05–2020/21 (Messi's
career), plus the complete 2015/16 season with all 20 clubs, plus the Champions League finals of both clubs
(finals only: the open data has no other Champions League matches of theirs).

| Category | Matches | Question it answers |
|---|---|---|
| `clasico` | 29 | How did the two styles change? (the analysis above) |
| `barcelona_vs_top10` | 235 | How did La Liga's strongest clubs play against Barcelona? |
| `barcelona_all` | 524 | Is a Clásico different from Barcelona's other league matches? |
| `season_2015_16` | 380 | Every club, every match; top-10 clubs against each other; Benítez vs Zidane at Real Madrid |
| `top10_2015_16` | 90 | 2015/16 matches between two top-10 clubs |
| `ucl_finals` | 7 | Were the Champions League finals played differently? (Barcelona 2009, 2011, 2015; Real Madrid 2014, 2016, 2017, 2018) |

"Top-10 clubs" are not picked by hand: they are the 10 clubs with the most top-10 finishes 2004/05–2020/21,
computed from every league result ([`scripts/standings.py`](scripts/standings.py), La Liga's head-to-head
tie-breaks included), ties broken by average final position: Barcelona, Real Madrid, Sevilla, Atlético Madrid,
Villarreal, Valencia, Athletic Club, Real Sociedad, Getafe, Málaga.

First results, with 90% bootstrap intervals ([`analysis/intervals.py`](analysis/intervals.py), same method as
the Clásico intervals; `data/league/intervals.csv` has every metric):

| Barcelona's PPDA (higher = less pressure) | 2004-09 | 2009-13 | 2013-17 | 2017-21 |
|---|---|---|---|---|
| vs Real Madrid (Clásicos) | 10.0 | **9.5** | 12.0 | **17.9** |
| vs other top-10 clubs | 10.7 | 11.9 | 11.1 | 14.7 |
| vs every other club | 9.9 | 11.1 | 11.6 | 12.9 |
| Clásico − other clubs | +0.1 [−1.4, +1.7] | **−1.6 [−2.8, −0.2]** | +0.4 [−1.5, +2.9] | **+4.9 [+2.8, +7.5]** |

**A Clásico is different, and the difference flipped.** Under Guardiola Barcelona pressed *harder* against Real
Madrid than against anyone else; by 2017-21 it pressed clearly *less* in the Clásicos than against the rest of the
league. Against every other club the press loosened too, but slowly (+1.9 [+0.9, +2.8] from 2009-13 to 2017-21).
In every period Barcelona had less of the ball in a Clásico (−5 to −11 points of possession, all clear).

Smaller clubs moved to back threes and fives against Barcelona after 2017 (35% of matches, against 10% for the
top-10 clubs, which mostly kept a back four).

**Champions League finals were played differently.** A final is one match, so it is set against the team's single
matches that season, not against an average ([`data/league/finals.csv`](data/league/finals.csv)). In the 2009 final
Barcelona had 51% of the ball, less than in any of its 31 league matches that season, reached its shots after 3.3
passes (fewer than in any league match) and attacked slower than in any of them. In the 2011 final it barely
pressed (PPDA 31.8, above every league match) because Manchester United hardly built up. 17 of the 49
final-metric pairs fall outside the middle 90% of the team's matches. Real Madrid's finals other than 2016 can only
be compared with its Clásicos, the only other Real Madrid matches in the data.

**Benítez → Zidane (Real Madrid 2015/16).** 2.06 points per match under Benítez (18 matches), 2.65 under Zidane (20).
The only clear change in how the team played is slower attacks: 2.14 → 1.88 m/s, −0.26 [−0.42, −0.09]. Press
success (+3.2 [−0.8, +7.2] points) and PPDA (−1.0 [−3.1, +1.1]) moved, but within what the match sample allows.

```bash
pip install -r requirements.txt
docker compose up -d                    # PostgreSQL 16 on localhost:5434
python3 scripts/download.py             # ~2.5 GB of event files, in parallel; resumable
python3 scripts/load_db.py              # every match into PostgreSQL (~5 min); `clasico` or `ucl_finals` alone
python3 analysis/league.py              # tables in data/league/
python3 analysis/intervals.py           # 90% intervals -> data/league/intervals.csv (seconds)
python3 -m unittest tests.test_frames tests.test_finals tests.test_bootstrap   # pandas and numpy == reference
```

The schema ([`db/schema.sql`](db/schema.sql)) keeps the common event fields as columns and the full StatsBomb
event as `jsonb`, so a new metric never needs a new download. Example:

```sql
-- How Barcelona's opponents lined up, top-10 clubs vs the rest
SELECT c.team_name IN (SELECT team_name FROM top_clubs) AS top10_club, f.formation, count(*)
FROM formations f
JOIN teams c USING (team_id)
JOIN match_categories mc ON mc.match_id = f.match_id AND mc.category = 'barcelona_all'
WHERE f.starting AND c.team_name <> 'Barcelona'
GROUP BY 1, 2 ORDER BY 1, 3 DESC;
```

## Project layout

```
clasico/            shared definitions (one place for every rule)
  data.py           download with retries + local cache (data/raw)
  events.py         time, ball-strip detection, possessions, zones, game state
  output.py         JSON/CSV writing; each JSON carries the code that produced it
  db.py             PostgreSQL: connection, schema, COPY loader, match categories
  frames.py         the metrics in pandas, for any category of matches
  bootstrap.py      match-level bootstrap with numpy
db/schema.sql       tables (matches, lineups, events, standings) and views (formations, top_clubs)
analysis/           league.py (tables) and intervals.py (bootstrap) -> data/league/
scripts/            pipeline steps, run in this order by pipeline.py
  build.py          match-team metrics + every non-penalty shot
  losses.py         every ball lost after a controlled touch, with the opponent shot that followed
  strips.py         players pressing each loss
  game_state.py     main metrics split by Ahead / Level / Behind
  uncertainty.py    bootstrap intervals for period averages and period-to-period changes
  loss_table.py     flat loss table (CSV) for spreadsheet use
  download.py       all La Liga event files, in parallel (not part of pipeline.py)
  load_db.py        load matches, standings and categories into PostgreSQL
  standings.py      final tables from every result -> data/reference/standings.csv
site/               build_site.py (static dashboard -> docs/index.html), readme_charts.py (docs/img/*.svg)
docs/               published site: index.html + README charts
tests/              unit tests on hand-built events + consistency tests on outputs
data/processed/     outputs (data/raw is downloaded and not committed)
dashboard/          dashboard page source: index.html (El Clásico), league.html (League context, Special seasons)
.github/workflows/  CI: tests, freshness of generated files, full rebuild from raw data
```

## Run it

Python 3.10+ and the standard library only; nothing to install (the PostgreSQL layer above needs `requirements.txt`).

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

League results for the standings: [engsoccerdata](https://github.com/jalapic/engsoccerdata) by James Curley.

Event data © StatsBomb, released as open data under their
[user agreement](https://github.com/statsbomb/open-data/blob/master/LICENSE.pdf).
