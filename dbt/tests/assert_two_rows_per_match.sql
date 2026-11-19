-- Every match has exactly two team rows (fails on any match that does not).
select match_id, count(*) as n
from {{ ref('fct_match_team') }}
group by 1
having count(*) <> 2
