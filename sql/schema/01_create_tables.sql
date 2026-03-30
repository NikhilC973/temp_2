-- ============================================================
-- South Shore Sentiment Study — PostgreSQL Star Schema
-- Fact table + dimension tables for analytical queries
-- ============================================================

-- Dimension: Platforms
CREATE TABLE IF NOT EXISTS dim_platform (
    platform_key    SERIAL PRIMARY KEY,
    platform_name   VARCHAR(50) NOT NULL UNIQUE,
    platform_color  VARCHAR(7),
    description     TEXT
);

INSERT INTO dim_platform (platform_name, platform_color, description) VALUES
    ('reddit',       '#FF4500', '14 subreddits including r/Chicago, r/news, r/immigration'),
    ('youtube',      '#FF0000', 'YouTube video descriptions and comment threads'),
    ('news_comment', '#1DA1F2', 'Block Club Chicago, WBEZ, Sun-Times, South Side Weekly, AP')
ON CONFLICT (platform_name) DO NOTHING;

-- Dimension: Temporal Phases
CREATE TABLE IF NOT EXISTS dim_phase (
    phase_key       SERIAL PRIMARY KEY,
    phase_id        VARCHAR(30) NOT NULL UNIQUE,
    phase_label     VARCHAR(100),
    start_date      DATE NOT NULL,
    end_date        DATE NOT NULL,
    phase_order     INT NOT NULL,
    description     TEXT
);

INSERT INTO dim_phase (phase_id, phase_label, start_date, end_date, phase_order, description) VALUES
    ('pre',           'Pre-Raid Baseline',           '2025-09-16', '2025-09-29', 1, 'Community anxiety before the event'),
    ('event',         'Event Window (±24h)',          '2025-09-29', '2025-10-01', 2, 'Operation Midway Blitz execution'),
    ('post_week1',    'Post-Raid Week 1',            '2025-10-01', '2025-10-07', 3, 'Immediate aftermath and crisis response'),
    ('post_week2',    'Post-Raid Week 2',            '2025-10-08', '2025-10-14', 4, 'Organizing begins, media attention grows'),
    ('post_weeks3_5', 'Extended Monitoring',          '2025-10-15', '2025-11-07', 5, 'Sustained discourse, investigations published'),
    ('court_action',  'Court Action & Tenants Union', '2025-11-08', '2025-11-30', 6, 'Legal proceedings and collective organizing'),
    ('displacement',  'Forced Displacement',          '2025-12-01', '2025-12-12', 7, 'Eviction deadline and building closure')
ON CONFLICT (phase_id) DO NOTHING;

-- Dimension: Neighborhoods
CREATE TABLE IF NOT EXISTS dim_neighborhood (
    neighborhood_key SERIAL PRIMARY KEY,
    neighborhood     VARCHAR(100) NOT NULL UNIQUE,
    search_terms     TEXT[]
);

-- Dimension: Date (calendar table for time-series joins)
CREATE TABLE IF NOT EXISTS dim_date (
    date_key        DATE PRIMARY KEY,
    day_of_week     VARCHAR(10),
    week_number     INT,
    month_name      VARCHAR(20),
    is_weekend      BOOLEAN,
    days_from_raid  INT  -- days relative to Sep 30 (T_ZERO)
);

-- Fact: Posts (grain = one post or comment)
CREATE TABLE IF NOT EXISTS fact_posts (
    post_id             VARCHAR(64) PRIMARY KEY,
    platform_key        INT REFERENCES dim_platform(platform_key),
    phase_key           INT REFERENCES dim_phase(phase_key),
    post_date           DATE REFERENCES dim_date(date_key),
    source_name         VARCHAR(200),
    post_type           VARCHAR(20),
    word_count          INT,
    -- Sentiment
    vader_compound      FLOAT,
    roberta_positive    FLOAT,
    roberta_negative    FLOAT,
    roberta_neutral     FLOAT,
    sentiment_label     VARCHAR(10),
    -- Emotions (GoEmotions → 8 targets)
    emo_fear            FLOAT,
    emo_anger           FLOAT,
    emo_sadness         FLOAT,
    emo_joy             FLOAT,
    emo_surprise        FLOAT,
    emo_disgust         FLOAT,
    emo_gratitude       FLOAT,
    emo_pride           FLOAT,
    dominant_emotion    VARCHAR(20),
    emotion_confidence  FLOAT,
    -- Topics
    topic_id            INT,
    topic_label         VARCHAR(200),
    -- Engagement
    score               INT DEFAULT 0,
    like_count          INT DEFAULT 0,
    reply_count         INT DEFAULT 0,
    view_count          INT DEFAULT 0
);

-- Bridge: Post ↔ Neighborhood (many-to-many)
CREATE TABLE IF NOT EXISTS bridge_post_neighborhood (
    post_id             VARCHAR(64) REFERENCES fact_posts(post_id),
    neighborhood_key    INT REFERENCES dim_neighborhood(neighborhood_key),
    PRIMARY KEY (post_id, neighborhood_key)
);

-- Performance indexes
CREATE INDEX IF NOT EXISTS idx_fact_posts_date ON fact_posts(post_date);
CREATE INDEX IF NOT EXISTS idx_fact_posts_platform ON fact_posts(platform_key);
CREATE INDEX IF NOT EXISTS idx_fact_posts_phase ON fact_posts(phase_key);
CREATE INDEX IF NOT EXISTS idx_fact_posts_emotion ON fact_posts(dominant_emotion);
CREATE INDEX IF NOT EXISTS idx_fact_posts_sentiment ON fact_posts(sentiment_label);
