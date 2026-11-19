-- A team cannot win more pressures than it made.
select match_team_key from {{ ref('fct_match_team') }} where pressures_won_5s > pressures
