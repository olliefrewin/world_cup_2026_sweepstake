-- SQLite schema for the World Cup 2026 sweepstake app.

CREATE TABLE IF NOT EXISTS participants (
    id   INTEGER PRIMARY KEY,
    name TEXT NOT NULL UNIQUE
);

CREATE TABLE IF NOT EXISTS part1_submissions (
    id               INTEGER PRIMARY KEY,
    participant_id   INTEGER NOT NULL REFERENCES participants(id),
    submitted_on     TEXT,
    uploaded_at      TEXT NOT NULL,
    filename         TEXT NOT NULL,
    group_picks_json TEXT NOT NULL,  -- {"A": ["Mexico", "South Korea"], ...}
    finalist_1       TEXT,
    finalist_2       TEXT,
    winner           TEXT,
    golden_boot_raw  TEXT,
    UNIQUE(participant_id)
);

CREATE TABLE IF NOT EXISTS part2_submissions (
    id                    INTEGER PRIMARY KEY,
    participant_id        INTEGER NOT NULL REFERENCES participants(id),
    uploaded_at           TEXT NOT NULL,
    filename              TEXT NOT NULL,
    r32_pairs_json        TEXT NOT NULL,
    r32_winners_json      TEXT NOT NULL,
    r16_winners_json      TEXT NOT NULL,
    qf_winners_json       TEXT NOT NULL,
    sf_winners_json       TEXT NOT NULL,
    champion              TEXT,
    tiebreaker_final_goals INTEGER,
    UNIQUE(participant_id)
);

-- Actuals from the API (keyed by slot, e.g. "group_winner.A", "r32_winner.L1", "champion")
CREATE TABLE IF NOT EXISTS actuals_api (
    key        TEXT PRIMARY KEY,
    value      TEXT,
    fetched_at TEXT NOT NULL
);

-- Manual corrections applied on top of API actuals
CREATE TABLE IF NOT EXISTS actuals_override (
    key    TEXT PRIMARY KEY,
    value  TEXT,
    set_at TEXT NOT NULL,
    note   TEXT
);

-- Effective view: override wins if present, otherwise API value
CREATE VIEW IF NOT EXISTS actuals_effective AS
    SELECT
        COALESCE(o.key, a.key) AS key,
        COALESCE(o.value, a.value) AS value
    FROM actuals_api a
    LEFT JOIN actuals_override o ON a.key = o.key
    UNION
    SELECT key, value
    FROM actuals_override
    WHERE key NOT IN (SELECT key FROM actuals_api);

CREATE TABLE IF NOT EXISTS golden_boot_resolutions (
    participant_id   INTEGER PRIMARY KEY REFERENCES participants(id),
    raw_text         TEXT NOT NULL,
    resolved_canonical TEXT,          -- NULL means no match
    status           TEXT NOT NULL,   -- 'pending', 'matched', 'rejected'
    resolved_at      TEXT
);

-- Tracks every outbound API call for quota monitoring
CREATE TABLE IF NOT EXISTS api_calls (
    id          INTEGER PRIMARY KEY,
    endpoint    TEXT NOT NULL,
    called_at   TEXT NOT NULL,
    status_code INTEGER,
    cached      INTEGER NOT NULL DEFAULT 0  -- 0=false, 1=true
);

-- Key-value settings store
CREATE TABLE IF NOT EXISTS settings (
    key   TEXT PRIMARY KEY,
    value TEXT
);
-- Expected keys: 'api_key', 'last_refresh_at'
