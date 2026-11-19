-- League-wide event store for StatsBomb open data (and, later, other providers).
-- Applied by scripts/load_db.py; safe to run again (everything is IF NOT EXISTS / OR REPLACE).

CREATE TABLE IF NOT EXISTS competitions (
    competition_id   integer NOT NULL,
    season_id        integer NOT NULL,
    competition_name text    NOT NULL,
    season_name      text    NOT NULL,
    PRIMARY KEY (competition_id, season_id)
);

CREATE TABLE IF NOT EXISTS teams (
    team_id   integer PRIMARY KEY,
    team_name text    NOT NULL UNIQUE
);

CREATE TABLE IF NOT EXISTS players (
    player_id   integer PRIMARY KEY,
    player_name text    NOT NULL
);

CREATE TABLE IF NOT EXISTS matches (
    match_id       integer PRIMARY KEY,
    provider       text    NOT NULL DEFAULT 'statsbomb',
    competition_id integer NOT NULL,
    season_id      integer NOT NULL,
    season_name    text    NOT NULL,
    match_date     date    NOT NULL,
    match_week     integer,
    home_team_id   integer NOT NULL REFERENCES teams,
    away_team_id   integer NOT NULL REFERENCES teams,
    home_score     integer NOT NULL,
    away_score     integer NOT NULL,
    home_manager   text,
    away_manager   text,
    stadium        text,
    referee        text,
    FOREIGN KEY (competition_id, season_id) REFERENCES competitions
);

CREATE TABLE IF NOT EXISTS lineups (
    match_id      integer NOT NULL REFERENCES matches ON DELETE CASCADE,
    team_id       integer NOT NULL REFERENCES teams,
    player_id     integer NOT NULL REFERENCES players,
    jersey_number integer,
    positions     jsonb,   -- [{position, from, to, start_reason, end_reason}, ...]
    PRIMARY KEY (match_id, team_id, player_id)
);

-- One row per event. Frequently used fields are columns; the full StatsBomb event is kept in raw,
-- so nothing is lost and new metrics never need a re-download.
CREATE TABLE IF NOT EXISTS events (
    event_id           uuid    PRIMARY KEY,
    match_id           integer NOT NULL REFERENCES matches ON DELETE CASCADE,
    idx                integer NOT NULL,            -- StatsBomb 'index': order within the match
    period             integer NOT NULL,
    minute             integer NOT NULL,
    second             integer NOT NULL,
    ts                 double precision NOT NULL,   -- seconds since the start of the period
    type               text    NOT NULL,
    team_id            integer NOT NULL REFERENCES teams,
    player_id          integer REFERENCES players,
    possession         integer NOT NULL,
    possession_team_id integer NOT NULL REFERENCES teams,
    play_pattern       text    NOT NULL,
    x                  double precision,            -- 120 x 80 pitch, the acting team attacks left to right
    y                  double precision,
    end_x              double precision,
    end_y              double precision,
    outcome            text,                        -- pass/shot/dribble/duel/... outcome, NULL = success for passes
    subtype            text,                        -- shot type, duel type, pass type, ...
    xg                 double precision,
    duration           double precision,
    under_pressure     boolean NOT NULL DEFAULT false,
    raw                jsonb   NOT NULL,
    UNIQUE (match_id, idx)
);
CREATE INDEX IF NOT EXISTS events_match_type ON events (match_id, type);
CREATE INDEX IF NOT EXISTS events_team ON events (team_id);
-- time-window lookups within a half (press success: own possession within 5 s), used by the dbt models
CREATE INDEX IF NOT EXISTS events_match_period_ts ON events (match_id, period, ts);

-- Final league tables, computed from every result of the season (football-data.co.uk),
-- not only the matches in the event data.
CREATE TABLE IF NOT EXISTS standings (
    season_name text    NOT NULL,
    position    integer NOT NULL,
    team_name   text    NOT NULL,   -- StatsBomb spelling
    played      integer NOT NULL,
    won         integer NOT NULL,
    drawn       integer NOT NULL,
    lost        integer NOT NULL,
    goals_for   integer NOT NULL,
    goals_against integer NOT NULL,
    points      integer NOT NULL,
    PRIMARY KEY (season_name, team_name)
);

-- A match can be in several categories (a Clásico is also a Barcelona match against a top-10 club).
CREATE TABLE IF NOT EXISTS match_categories (
    match_id integer NOT NULL REFERENCES matches ON DELETE CASCADE,
    category text    NOT NULL,
    PRIMARY KEY (match_id, category)
);

-- Formation at kick-off and after every tactical shift.
CREATE OR REPLACE VIEW formations AS
SELECT e.match_id, e.team_id, t.team_name, e.period, e.minute, e.idx,
       e.type = 'Starting XI' AS starting,
       e.raw -> 'tactics' ->> 'formation' AS formation
FROM events e JOIN teams t USING (team_id)
WHERE e.type IN ('Starting XI', 'Tactical Shift');

-- Matches with readable team names, for ad-hoc SQL.
CREATE OR REPLACE VIEW match_list AS
SELECT m.match_id, m.season_name, m.match_date, h.team_name AS home, a.team_name AS away,
       m.home_score, m.away_score, m.home_manager, m.away_manager, m.competition_id
FROM matches m
JOIN teams h ON h.team_id = m.home_team_id
JOIN teams a ON a.team_id = m.away_team_id;

-- The 10 clubs with the most top-10 finishes 2004/05-2020/21; ties broken by average final position.
CREATE OR REPLACE VIEW top_clubs AS
SELECT team_name,
       count(*) FILTER (WHERE position <= 10) AS top10_finishes,
       round(avg(position), 1)                AS avg_position,
       count(*)                               AS seasons_in_liga
FROM standings
GROUP BY team_name
ORDER BY top10_finishes DESC, avg(position)
LIMIT 10;
