select
    m.match_id,
    m.match_date,
    m.season_name,
    m.competition,
    h.team_name                                                     as home_team,
    a.team_name                                                     as away_team,
    m.home_score,
    m.away_score,
    coalesce((select string_agg(c.category, '|' order by c.category)
              from {{ ref('stg_match_categories') }} c where c.match_id = m.match_id), '') as categories
from {{ ref('stg_matches') }} m
join {{ ref('stg_teams') }} h on h.team_id = m.home_team_id
join {{ ref('stg_teams') }} a on a.team_id = m.away_team_id
