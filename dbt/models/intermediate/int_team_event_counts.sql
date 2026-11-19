-- Counts per team and match in regular time (periods 1-2), with the reference definitions
-- (scripts/build.py): a defensive action is a tackle, interception or foul at x >= 48; a build-up pass is a pass
-- at x <= 72 (each team's own frame, attacking left to right).
select
    match_id,
    team_id,
    count(*) filter (where event_type = 'Pass')                                            as passes,
    count(*) filter (where event_type = 'Pass' and x <= 72)                                as buildup_passes,
    count(*) filter (where event_type = 'Pressure')                                        as pressures,
    count(*) filter (where x >= 48 and (event_type in ('Interception', 'Foul Committed')
                                        or (event_type = 'Duel' and subtype = 'Tackle')))  as def_actions,
    count(*) filter (where event_type = 'Shot' and subtype <> 'Penalty')                   as np_shots,
    coalesce(sum(xg) filter (where event_type = 'Shot' and subtype <> 'Penalty'), 0)       as np_xg
from {{ ref('stg_events') }}
where is_regular_time
group by 1, 2
