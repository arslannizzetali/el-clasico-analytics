-- One team's goals for are the other's goals against.
select a.match_id
from {{ ref('fct_match_team') }} a
join {{ ref('fct_match_team') }} b on b.match_id = a.match_id and b.team_id <> a.team_id
where a.goals_for <> b.goals_against
