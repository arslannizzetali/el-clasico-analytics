-- One row per StatsBomb event, typed and renamed; no business logic.
select
    event_id,
    match_id,
    idx                         as event_index,
    period,
    minute,
    ts                          as seconds_in_period,
    type                        as event_type,
    team_id,
    player_id,
    possession,
    possession_team_id,
    play_pattern,
    x,
    y,
    end_x,
    end_y,
    outcome,
    subtype,
    xg,
    period <= 2                 as is_regular_time
from {{ source('statsbomb', 'events') }}
