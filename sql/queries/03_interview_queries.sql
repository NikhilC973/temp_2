-- ============================================================
-- STANDALONE ANALYTICAL QUERIES
-- Demonstrate SQL fluency: CTEs, window functions, pivots
-- ============================================================

-- Q1: Which platform reacted fastest after the raid?
WITH ranked_posts AS (
    SELECT
        p.platform_name,
        f.post_date,
        f.post_id,
        ROW_NUMBER() OVER (
            PARTITION BY p.platform_name
            ORDER BY f.post_date
        ) AS post_rank
    FROM fact_posts f
    JOIN dim_platform p ON f.platform_key = p.platform_key
    JOIN dim_phase ph ON f.phase_key = ph.phase_key
    WHERE ph.phase_id = 'event'
)
SELECT
    platform_name,
    MIN(post_date) AS first_post_date,
    MAX(post_date) AS hundredth_post_date,
    MAX(post_date) - MIN(post_date) AS time_to_100_posts
FROM ranked_posts
WHERE post_rank <= 100
GROUP BY platform_name
ORDER BY first_post_date;


-- Q2: Emotional crossover — when does gratitude overtake fear?
SELECT
    post_date,
    ROUND(AVG(emo_fear)::numeric, 3)      AS daily_fear,
    ROUND(AVG(emo_gratitude)::numeric, 3)  AS daily_gratitude,
    ROUND(AVG(emo_pride)::numeric, 3)      AS daily_pride,
    CASE
        WHEN AVG(emo_gratitude) > AVG(emo_fear) THEN 'GRATITUDE_LEADS'
        ELSE 'FEAR_LEADS'
    END AS emotional_regime
FROM fact_posts
GROUP BY post_date
ORDER BY post_date;


-- Q3: Reddit vs YouTube vs News sentiment divergence by phase
SELECT
    ph.phase_label,
    ROUND(AVG(CASE WHEN p.platform_name = 'reddit' THEN f.vader_compound END)::numeric, 3)
        AS reddit_sentiment,
    ROUND(AVG(CASE WHEN p.platform_name = 'youtube' THEN f.vader_compound END)::numeric, 3)
        AS youtube_sentiment,
    ROUND(AVG(CASE WHEN p.platform_name = 'news_comment' THEN f.vader_compound END)::numeric, 3)
        AS news_sentiment,
    ROUND((
        AVG(CASE WHEN p.platform_name = 'reddit' THEN f.vader_compound END) -
        AVG(CASE WHEN p.platform_name = 'youtube' THEN f.vader_compound END)
    )::numeric, 3) AS reddit_youtube_gap
FROM fact_posts f
JOIN dim_platform p ON f.platform_key = p.platform_key
JOIN dim_phase ph ON f.phase_key = ph.phase_key
GROUP BY ph.phase_label, ph.phase_order
ORDER BY ph.phase_order;


-- Q4: 7-day rolling average sentiment with volatility bands
SELECT
    post_date,
    COUNT(*)                                          AS daily_posts,
    ROUND(AVG(vader_compound)::numeric, 3)            AS daily_sentiment,
    ROUND(AVG(AVG(vader_compound)) OVER (
        ORDER BY post_date ROWS BETWEEN 6 PRECEDING AND CURRENT ROW
    )::numeric, 3)                                    AS rolling_7d_avg,
    ROUND(STDDEV(AVG(vader_compound)) OVER (
        ORDER BY post_date ROWS BETWEEN 6 PRECEDING AND CURRENT ROW
    )::numeric, 3)                                    AS rolling_7d_stddev
FROM fact_posts
GROUP BY post_date
ORDER BY post_date;


-- Q5: Which subreddits drove the most negative sentiment?
SELECT
    source_name,
    COUNT(*)                                     AS post_count,
    ROUND(AVG(vader_compound)::numeric, 3)       AS avg_sentiment,
    ROUND(PERCENTILE_CONT(0.25) WITHIN GROUP
        (ORDER BY vader_compound)::numeric, 3)   AS p25_sentiment,
    COUNT(*) FILTER (WHERE sentiment_label = 'negative')
        * 100.0 / COUNT(*)                       AS pct_negative,
    MODE() WITHIN GROUP (ORDER BY dominant_emotion) AS most_common_emotion
FROM fact_posts f
JOIN dim_platform p ON f.platform_key = p.platform_key
WHERE p.platform_name = 'reddit'
GROUP BY source_name
HAVING COUNT(*) >= 10
ORDER BY avg_sentiment ASC;


-- Q6: Emotion co-occurrence — do fear and anger travel together?
SELECT
    ROUND(CORR(emo_fear, emo_anger)::numeric, 3)     AS fear_anger_corr,
    ROUND(CORR(emo_fear, emo_sadness)::numeric, 3)   AS fear_sadness_corr,
    ROUND(CORR(emo_anger, emo_disgust)::numeric, 3)  AS anger_disgust_corr,
    ROUND(CORR(emo_gratitude, emo_pride)::numeric, 3) AS gratitude_pride_corr,
    ROUND(CORR(emo_joy, emo_gratitude)::numeric, 3)  AS joy_gratitude_corr
FROM fact_posts;


-- Q7: Post volume spike detection (>2σ above mean)
WITH daily_stats AS (
    SELECT
        post_date,
        COUNT(*) AS daily_count,
        AVG(COUNT(*)) OVER () AS global_avg,
        STDDEV(COUNT(*)) OVER () AS global_stddev
    FROM fact_posts
    GROUP BY post_date
)
SELECT
    post_date,
    daily_count,
    ROUND(global_avg::numeric, 1) AS avg_daily,
    ROUND((daily_count - global_avg) / NULLIF(global_stddev, 0)::numeric, 2)
        AS z_score,
    CASE
        WHEN daily_count > global_avg + 2 * global_stddev THEN 'SPIKE'
        WHEN daily_count < global_avg - 1 * global_stddev THEN 'DROP'
        ELSE 'NORMAL'
    END AS volume_signal
FROM daily_stats
ORDER BY post_date;
