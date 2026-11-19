-- One row per team per match: the counting metrics of the reference pipeline in SQL.
-- Possession-sequence metrics (passes before a shot, turnovers, ball strips) stay in Python (clasico/frames.py,
-- scripts/build.py): they need event order within a possession, which is clearer there than in SQL.
with mt as (select * from {{ ref('int_match_teams') }}),
     c  as (select * from {{ ref('int_team_event_counts') }}),
     pw as (select * from {{ ref('int_pressures_won') }})
select
    mt.match_id || '|' || t.team_name                                       as match_team_key,
    mt.match_id,
    mt.team_id,
    t.team_name                                                             as team,
    o.team_name                                                             as opponent,
    mt.venue,
    mt.coach,
    mt.goals_for,
    mt.goals_against,
    case when mt.goals_for > mt.goals_against then 3
         when mt.goals_for = mt.goals_against then 1 else 0 end            as points,
    coalesce(c.passes, 0)                                                   as passes,
    coalesce(c.pressures, 0)                                                as pressures,
    coalesce(pw.pressures_won_5s, 0)                                        as pressures_won_5s,
    coalesce(c.def_actions, 0)                                              as def_actions,
    coalesce(oc.passes, 0)                                                  as opp_passes,
    coalesce(oc.buildup_passes, 0)                                          as opp_buildup_passes,
    coalesce(c.np_shots, 0)                                                 as np_shots,
    round(coalesce(c.np_xg, 0)::numeric, 2)                                 as np_xg,
    -- rates unrounded: round when presenting (Python rounds half to even, SQL numeric half away from zero)
    coalesce(oc.buildup_passes, 0)::float / greatest(coalesce(c.def_actions, 0), 1)                as ppda,
    100.0 * pw.pressures_won_5s / nullif(c.pressures, 0)                    as press_success_pct
from mt
join {{ ref('stg_teams') }} t on t.team_id = mt.team_id
join {{ ref('stg_teams') }} o on o.team_id = mt.opponent_team_id
left join c         on c.match_id = mt.match_id  and c.team_id = mt.team_id
left join c as oc   on oc.match_id = mt.match_id and oc.team_id = mt.opponent_team_id
left join pw        on pw.match_id = mt.match_id and pw.team_id = mt.team_id
