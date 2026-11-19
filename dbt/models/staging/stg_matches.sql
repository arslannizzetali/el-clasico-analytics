select
    match_id,
    case competition_id when 11 then 'La Liga' when 16 then 'Champions League' else 'Other' end as competition,
    season_name,
    match_date,
    home_team_id,
    away_team_id,
    home_score,
    away_score,
    home_manager,
    away_manager
from {{ source('statsbomb', 'matches') }}
