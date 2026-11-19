# Using the data in Power BI or Tableau

`data/bi/` is a star schema built from the project's outputs by `python3 analysis/export_bi.py`. UTF-8,
comma-separated, ISO dates (`YYYY-MM-DD`), `True`/`False` for flags, empty cells for missing values.

## Tables

| Table | Grain | Key | What it holds |
|---|---|---|---|
| `dim_match` | one match | `match_id` | date, season, period, competition, home/away team and goals, one `is_<category>` flag per category |
| `dim_team` | one club | `team` | La Liga record 2004/05–2020/21: seasons, top-10 finishes, average position, `is_top10_club` |
| `standings` | club × season | `season`, `team` | final league tables from every result |
| `fact_match_team` | team × match | `match_id`, `team` | coach, formation, result, **raw counts** and per-match metrics, every league match and final |
| `fact_intervals` | metric × group × period | — | 90% bootstrap intervals: Clásico (reference) and league tables, periods, changes, contrasts |
| `fact_finals` | final × metric | `match_id`, `team`, `metric` | each final against the team's matches that season |
| `clasico_match_team`, `clasico_shots`, `clasico_losses` | Clásico detail | — | the reference pipeline's tables: turnover and strip metrics, every shot, every ball lost |

## Relationships

```
dim_match[match_id]  1 ──── *  fact_match_team[match_id]
dim_team[team]       1 ──── *  fact_match_team[team]
dim_team[team]       1 ──── *  fact_match_team[opponent]   (inactive in Power BI; use USERELATIONSHIP)
dim_match[match_id]  1 ──── *  fact_finals[match_id]
```

Filter on the `is_<category>` flags of `dim_match` to reproduce the dashboard's groups (`is_clasico`,
`is_barcelona_all`, `is_barcelona_vs_top10`, `is_season_2015_16`, `is_ucl_finals`).

## Measures: sum the parts, do not average the rates

A rate averaged over matches gives a short match the same weight as a long one and does not match the project's
numbers. Compute it from the summed counts:

```DAX
PPDA            = DIVIDE ( SUM ( fact_match_team[opp_buildup_passes] ), SUM ( fact_match_team[def_actions] ) )
Press success % = 100 * DIVIDE ( SUM ( fact_match_team[pressures_won_5s] ), SUM ( fact_match_team[pressures] ) )
Passes per shot = DIVIDE ( SUM ( fact_match_team[passes_before_shot_sum] ), SUM ( fact_match_team[open_play_shots] ) )
Possession %    = AVERAGE ( fact_match_team[possession_pct] )
Points / match  = AVERAGE ( fact_match_team[points] )
np xG / match   = AVERAGE ( fact_match_team[np_xg] )
```

Tableau: the same as calculated fields, e.g. `SUM([Opp Buildup Passes]) / SUM([Def Actions])`.

Check: with `is_clasico = True`, `team = "Barcelona"` and `dim_match[period] = "2017-21"`, PPDA should be **17.9**
(README, Key findings). Note that the league tables label the first period `2004-09` (they start in 2004/05) while
the Clásico tables say `2005-09`; the Clásicos in it are the same six matches.

Intervals cannot be recomputed by summing; take them from `fact_intervals` (`kind = period` for a group's value,
`change` between periods, `contrast` between groups; `clear = True` when the interval excludes zero).
