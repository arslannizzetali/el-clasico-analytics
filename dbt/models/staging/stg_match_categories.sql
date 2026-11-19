select match_id, category from {{ source('statsbomb', 'match_categories') }}
