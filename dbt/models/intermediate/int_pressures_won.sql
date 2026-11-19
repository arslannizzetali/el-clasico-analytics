-- A pressure is won when its team has the ball (any event with that team in possession) within the next
-- 5 seconds of the same period: seconds in (t, t + 5].
select
    p.match_id,
    p.team_id,
    count(*) filter (where exists (
        select 1
        from {{ ref('stg_events') }} e
        where e.match_id = p.match_id
          and e.period = p.period
          and e.seconds_in_period > p.seconds_in_period
          and e.seconds_in_period <= p.seconds_in_period + 5
          and e.possession_team_id = p.team_id
    )) as pressures_won_5s
from {{ ref('stg_events') }} p
where p.event_type = 'Pressure' and p.is_regular_time
group by 1, 2
