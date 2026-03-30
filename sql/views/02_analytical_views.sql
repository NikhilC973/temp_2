-- ============================================================
-- ANALYTICAL VIEWS — Power the BI dashboard and reporting
-- ============================================================

-- Daily sentiment by platform (core time-series)
CREATE OR REPLACE VIEW vw_daily_platform_sentiment AS
SELECT
    f.post_date,
    d.days_from_raid,
    p.platform_name,
    ph.phase_label,
    ph.phase_order,
    COUNT(*)                                    AS post_count,
    ROUND(AVG(f.vader_compound)::numeric, 3)    AS avg_sentiment,
    ROUND(AVG(f.emo_fear)::numeric, 3)          AS avg_fear,
    ROUND(AVG(f.emo_anger)::numeric, 3)         AS avg_anger,
    ROUND(AVG(f.emo_sadness)::numeric, 3)       AS avg_sadness,
    ROUND(AVG(f.emo_joy)::numeric, 3)           AS avg_joy,
    ROUND(AVG(f.emo_gratitude)::numeric, 3)     AS avg_gratitude,
    ROUND(AVG(f.emo_pride)::numeric, 3)         AS avg_pride,
    ROUND(STDDEV(f.vader_compound)::numeric, 3) AS sentiment_volatility
FROM fact_posts f
JOIN dim_platform p ON f.platform_key = p.platform_key
JOIN dim_phase ph ON f.phase_key = ph.phase_key
JOIN dim_date d ON f.post_date = d.date_key
GROUP BY f.post_date, d.days_from_raid, p.platform_name,
         ph.phase_label, ph.phase_order
ORDER BY f.post_date, p.platform_name;


-- Platform comparison (Reddit vs YouTube vs News)
CREATE OR REPLACE VIEW vw_platform_comparison AS
SELECT
    p.platform_name,
    COUNT(*)                                    AS total_posts,
    ROUND(AVG(f.vader_compound)::numeric, 3)    AS avg_sentiment,
    ROUND(AVG(f.emo_fear)::numeric, 3)          AS avg_fear,
    ROUND(AVG(f.emo_anger)::numeric, 3)         AS avg_anger,
    ROUND(AVG(f.emo_sadness)::numeric, 3)       AS avg_sadness,
    ROUND(AVG(f.emo_joy)::numeric, 3)           AS avg_joy,
    ROUND(AVG(f.emo_gratitude)::numeric, 3)     AS avg_gratitude,
    ROUND(AVG(f.emo_pride)::numeric, 3)         AS avg_pride,
    MODE() WITHIN GROUP (ORDER BY f.dominant_emotion) AS most_common_emotion,
    ROUND(AVG(f.like_count)::numeric, 1)        AS avg_engagement,
    COUNT(*) FILTER (WHERE f.sentiment_label = 'negative')
        * 100.0 / COUNT(*)                      AS pct_negative,
    COUNT(*) FILTER (WHERE f.sentiment_label = 'positive')
        * 100.0 / COUNT(*)                      AS pct_positive
FROM fact_posts f
JOIN dim_platform p ON f.platform_key = p.platform_key
GROUP BY p.platform_name;


-- Phase-over-phase emotional shift (key finding)
CREATE OR REPLACE VIEW vw_phase_emotion_trajectory AS
SELECT
    ph.phase_id,
    ph.phase_label,
    ph.phase_order,
    COUNT(*)                                    AS post_count,
    ROUND(AVG(f.vader_compound)::numeric, 3)    AS avg_sentiment,
    ROUND(AVG(f.emo_fear)::numeric, 3)          AS avg_fear,
    ROUND(AVG(f.emo_anger)::numeric, 3)         AS avg_anger,
    ROUND(AVG(f.emo_sadness)::numeric, 3)       AS avg_sadness,
    ROUND(AVG(f.emo_joy)::numeric, 3)           AS avg_joy,
    ROUND(AVG(f.emo_gratitude)::numeric, 3)     AS avg_gratitude,
    ROUND(AVG(f.emo_pride)::numeric, 3)         AS avg_pride,
    ROUND((AVG(f.emo_fear) - LAG(AVG(f.emo_fear))
        OVER (ORDER BY ph.phase_order))::numeric, 3) AS fear_delta,
    ROUND((AVG(f.emo_anger) - LAG(AVG(f.emo_anger))
        OVER (ORDER BY ph.phase_order))::numeric, 3) AS anger_delta,
    ROUND((AVG(f.emo_gratitude) - LAG(AVG(f.emo_gratitude))
        OVER (ORDER BY ph.phase_order))::numeric, 3) AS gratitude_delta
FROM fact_posts f
JOIN dim_phase ph ON f.phase_key = ph.phase_key
GROUP BY ph.phase_id, ph.phase_label, ph.phase_order
ORDER BY ph.phase_order;


-- Neighborhood impact heatmap
CREATE OR REPLACE VIEW vw_neighborhood_emotion_heatmap AS
SELECT
    n.neighborhood,
    ph.phase_label,
    ph.phase_order,
    COUNT(*)                                 AS post_count,
    ROUND(AVG(f.vader_compound)::numeric, 3) AS avg_sentiment,
    ROUND(AVG(f.emo_fear)::numeric, 3)       AS avg_fear,
    ROUND(AVG(f.emo_anger)::numeric, 3)      AS avg_anger
FROM fact_posts f
JOIN bridge_post_neighborhood bpn ON f.post_id = bpn.post_id
JOIN dim_neighborhood n ON bpn.neighborhood_key = n.neighborhood_key
JOIN dim_phase ph ON f.phase_key = ph.phase_key
GROUP BY n.neighborhood, ph.phase_label, ph.phase_order
ORDER BY ph.phase_order, n.neighborhood;


-- Platform × Phase cross-tabulation
CREATE OR REPLACE VIEW vw_platform_phase_matrix AS
SELECT
    ph.phase_label,
    ph.phase_order,
    p.platform_name,
    COUNT(*)                                    AS post_count,
    ROUND(AVG(f.vader_compound)::numeric, 3)    AS avg_sentiment,
    ROUND(AVG(f.emo_fear)::numeric, 3)          AS avg_fear,
    ROUND(AVG(f.emo_anger)::numeric, 3)         AS avg_anger,
    ROUND(AVG(f.emo_gratitude)::numeric, 3)     AS avg_gratitude,
    MODE() WITHIN GROUP (ORDER BY f.dominant_emotion) AS dominant_emotion
FROM fact_posts f
JOIN dim_platform p ON f.platform_key = p.platform_key
JOIN dim_phase ph ON f.phase_key = ph.phase_key
GROUP BY ph.phase_label, ph.phase_order, p.platform_name
ORDER BY ph.phase_order, p.platform_name;


-- Topics per phase with sentiment context
CREATE OR REPLACE VIEW vw_topic_phase_summary AS
SELECT
    ph.phase_label,
    f.topic_label,
    COUNT(*)                                    AS topic_count,
    ROUND(AVG(f.vader_compound)::numeric, 3)    AS avg_sentiment,
    MODE() WITHIN GROUP (ORDER BY f.dominant_emotion) AS dominant_emotion,
    ROUND(AVG(f.emo_anger)::numeric, 3)         AS avg_anger
FROM fact_posts f
JOIN dim_phase ph ON f.phase_key = ph.phase_key
WHERE f.topic_label IS NOT NULL
GROUP BY ph.phase_label, f.topic_label
HAVING COUNT(*) >= 5
ORDER BY ph.phase_label, topic_count DESC;


-- Engagement vs sentiment (do angry posts get more engagement?)
CREATE OR REPLACE VIEW vw_engagement_sentiment AS
SELECT
    p.platform_name,
    f.sentiment_label,
    f.dominant_emotion,
    COUNT(*)                              AS post_count,
    ROUND(AVG(f.like_count)::numeric, 1)  AS avg_likes,
    ROUND(AVG(f.reply_count)::numeric, 1) AS avg_replies,
    ROUND(AVG(f.score)::numeric, 1)       AS avg_score,
    ROUND(AVG(f.view_count)::numeric, 0)  AS avg_views
FROM fact_posts f
JOIN dim_platform p ON f.platform_key = p.platform_key
GROUP BY p.platform_name, f.sentiment_label, f.dominant_emotion
ORDER BY avg_likes DESC;
