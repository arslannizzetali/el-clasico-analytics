-- Two rows per match: each team with its opponent, venue and result.
select
    m.match_id,
    m.home_team_id                                  as team_id,
    m.away_team_id                                  as opponent_team_id,
    'Home'                                          as venue,
    m.home_score                                    as goals_for,
    m.away_score                                    as goals_against,
    m.home_manager                                  as coach
from {{ ref('stg_matches') }} m
union all
select
    m.match_id,
    m.away_team_id,
    m.home_team_id,
    'Away',
    m.away_score,
    m.home_score,
    m.away_manager
from {{ ref('stg_matches') }} m
