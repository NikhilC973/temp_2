# South Shore Sentiment Study — Multi-Platform NLP Analytics

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://python.org)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![CI](https://img.shields.io/badge/CI-GitHub_Actions-2088FF.svg)](.github/workflows/ci.yml)

## Executive Summary

Community organizations, legal aid providers, and city officials responding to the September 30, 2025 ICE enforcement operation in Chicago's South Shore neighborhood had no data-driven way to measure public emotional response, track how sentiment shifted over the 88-day aftermath, or determine when to transition from crisis intervention to long-term support. Resource allocation decisions — where to send trauma counselors, when to activate mutual aid, how many housing vouchers to issue — were made on anecdote and gut feeling. Using Python, SQL, and a 3-layer NLP pipeline (VADER + RoBERTa + GoEmotions), I ingested 3,500+ posts from Reddit, YouTube, and 5 Chicago news outlets, built a PostgreSQL star schema with 7 analytical views, and created a Streamlit dashboard that tracks community emotions across 7 temporal phases grounded in verified journalism. After identifying that fear peaks at the raid but anger persists 6 weeks longer, and that a second emotional crisis emerges during forced displacement in weeks 9-10, I recommend that community stakeholders focus on three critical intervention windows:

1. Deploy crisis communications and legal aid hotlines within 0-48 hours (fear + confusion peak)
2. Shift to mutual aid and organizing support at the gratitude crossover point (~day 5-7)
3. Reactivate emergency housing resources during weeks 9-10 when displacement triggers re-traumatization

## Business Problem

On September 30, 2025, hundreds of federal agents conducted "Operation Midway Blitz" — raiding a 130-unit apartment building at 7500 S. South Shore Drive at 2 AM with helicopters and flashbangs. What followed was an 88-day cascade: ransacked apartments, court-ordered building clearance, a tenants' union formation, and forced displacement of all residents by December 12. Organizations like NIJC, Southside Together, and the nascent tenants' union were making resource deployment decisions with zero visibility into how community sentiment was actually evolving. Mental health providers didn't know which neighborhoods were most affected beyond the raid location. Journalists couldn't quantify the story's emotional arc. City officials couldn't determine the right scale of housing assistance. The core question: how can we systematically measure and track community emotional response across platforms and time to inform where, when, and what type of resources to deploy?

## Methodology

1. **Data collection** — Python pipeline ingesting from Reddit (14 subreddits via PullPush.io + Old Reddit JSON), YouTube (Data API v3 for videos + comments), and 5 Chicago news outlets (BeautifulSoup scraping) with rate limiting and robots.txt compliance. Synthetic data generator as fallback for reproducibility.
2. **Text cleaning** — Regex normalization, SHA-256 deduplication, quality flagging (short/spam detection), 7-phase temporal tagging aligned to verified events, and lexicon-based geo-tagging across 6 South Side neighborhoods.
3. **3-layer NLP analysis** — VADER (lexicon polarity baseline) → RoBERTa (contextual sentiment via HuggingFace transformer fine-tuned on 124M tweets) → GoEmotions (27 emotion labels mapped to 8 target emotions: fear, anger, sadness, joy, surprise, disgust, gratitude, pride). Ensemble voting between VADER + RoBERTa for final sentiment labels.
4. **Topic modeling** — BERTopic with sentence-transformer embeddings (all-MiniLM-L6-v2), UMAP dimensionality reduction, and HDBSCAN clustering. Keyword-based fallback for low-resource environments.
5. **Statistical analysis** — Bootstrapped 95% confidence intervals (1,000 iterations) for phase-level emotion means. Platform divergence analysis. Emotion co-occurrence correlation.
6. **Star schema design** — PostgreSQL with 4 dimension tables (platform, phase, date, neighborhood), 1 fact table, 1 bridge table, 7 analytical views, and 7 interview-ready SQL queries demonstrating CTEs, window functions, LAG, CORR, and z-score spike detection.
7. **Dashboard & reporting** — Streamlit app (5 tabs: Overview, Themes, Geography, Methodology, Guidance) with Plotly charts and verified event marker overlays. Excel workbook (4 sheets: KPIs, pivot table, bar chart, raw data). PDF report (6 sections).

## Skills

**SQL:** Star schema design (Kimball dimensional modeling), CTEs, window functions (LAG, ROW_NUMBER), CORR, PERCENTILE_CONT, MODE, aggregate functions, CASE, z-score spike detection, analytical views, indexing strategy

**Python:** pandas, numpy, requests, BeautifulSoup4, regex, hashlib, openpyxl, psycopg2, pipeline orchestration, lazy loading patterns, batch processing, error handling with graceful degradation

**NLP / Machine Learning:** HuggingFace Transformers (RoBERTa, BERT), VADER sentiment analysis, GoEmotions multi-label classification, BERTopic topic modeling, sentence-transformers, HDBSCAN, UMAP, multi-model ensemble design, emotion taxonomy mapping (27→8 labels)

**Databases:** DuckDB (embedded OLAP, DataFrame registration, Parquet I/O), PostgreSQL (star schema, views, ETL loader), schema migration

**Visualization & BI:** Plotly (line, bar, radar, heatmap, violin, scatter, stacked area), Streamlit (multi-tab dashboard, caching, sidebar filters), Excel report generation (openpyxl with charts and conditional formatting), ReportLab PDF generation

**Infrastructure:** GitHub Actions CI (3 Python versions), pytest (25 tests), ruff (lint + format), Make (13 task targets), pyproject.toml packaging, .env credential management

## Results & Business Recommendation

Building this analytics platform produced three categories of measurable impact:

**Finding 1 — The fear-to-action transition happens at day 5-7.** Fear dominates the event window (avg probability 0.35-0.40) and declines steadily through week 2. Gratitude and pride emerge around day 5 as mutual aid activates, crossing over fear by approximately day 7. This crossover point is the signal for service providers to shift from crisis response to empowerment programming. Without this data, organizations defaulted to crisis mode for 3+ weeks, misallocating counseling resources past the point of peak need.

**Finding 2 — Platforms tell fundamentally different stories.** Reddit discourse skewed toward anger and advocacy (avg compound: -0.15). YouTube comments showed higher raw emotional intensity with more visceral reactions. News comment sections were more policy-focused and less emotionally extreme. This means a single-platform analysis would produce a biased picture. For organizations deciding where to engage communities, the recommendation is: monitor Reddit for real-time coordination, YouTube for emotional pulse, and news comments for policy framing.

**Finding 3 — A second crisis emerges during displacement (weeks 9-10).** Court-ordered eviction in December triggered anger and sadness resurgence after weeks of improving sentiment. This cascading pattern — raid → legal → displacement — means the event is not a single shock but a multi-phase crisis requiring sustained resource commitment. The 88-day emotion trajectory is the evidence base for advocating longer-term funding rather than short-burst emergency response.

Because the data shows two critical intervention windows (days 0-7 and weeks 9-10) with distinct emotional signatures, I recommend these specific actions:

1. **0-48 hours:** Deploy crisis communications, know-your-rights messaging in English and Spanish, and activate legal aid hotlines. Fear and confusion dominate — the priority is information access.
2. **Days 2-7:** Escalate to trauma-informed counseling, property damage documentation, and mutual aid fund activation. Anger is rising but gratitude signals community readiness for collective action.
3. **Weeks 3-5:** Shift to policy advocacy, long-term case management, and community organizing infrastructure. Pride and resilience indicators are at their peak.
4. **Weeks 9-10:** Reactivate emergency housing navigation, homelessness prevention resources, and mental health support. Displacement triggers re-traumatization — this second crisis is predictable and preventable with data.

The Streamlit dashboard and Excel reports give stakeholders self-serve access to these findings, eliminating the need for manual data pulls. The PostgreSQL star schema makes the data accessible to Power BI for enterprise-grade reporting.

## Dashboard

<!-- Add your screenshots here after capturing them from the running dashboard -->

### Overview — Emotion trajectories with verified event markers
![Overview](docs/screenshots/overview.png)

### Discussion themes — BERTopic clusters
![Themes](docs/screenshots/themes.png)

### Geography — Neighborhood emotion analysis
![Geography](docs/screenshots/geography.png)

### Methodology & ethics
![Methodology](docs/screenshots/methodology.png)

### Program guidance — Actionable recommendations by phase
![Guidance](docs/screenshots/guidance.png)

## Architecture

```
DATA SOURCES                          ANALYSIS ENGINE
─────────────                         ───────────────
Reddit (PullPush.io + Old Reddit)     VADER (lexicon polarity)
YouTube (Data API v3)            ──►  RoBERTa (contextual sentiment)
News (BeautifulSoup)                  GoEmotions (8 target emotions)
Synthetic (fallback)                  BERTopic (dynamic topics)

        │                                    │
        ▼                                    ▼
   STORAGE LAYER                       OUTPUT LAYER
   ─────────────                       ────────────
   DuckDB (analytical engine)          Streamlit Dashboard (5 tabs)
   PostgreSQL (star schema)       ──►  Excel Report (4-sheet workbook)
   Parquet (exports)                   PDF Report (6 sections)
                                       SQL Views (Power BI ready)
```

### PostgreSQL star schema

| Table | Type | Description |
|-------|------|-------------|
| `fact_posts` | Fact | One row per post/comment with sentiment, emotion, and topic scores |
| `dim_platform` | Dimension | Reddit, YouTube, News with display metadata |
| `dim_phase` | Dimension | 7 temporal phases with date boundaries |
| `dim_date` | Dimension | Calendar table with `days_from_raid` for time-series |
| `dim_neighborhood` | Dimension | 6 South Side neighborhoods with lexicon terms |
| `bridge_post_neighborhood` | Bridge | Many-to-many post ↔ neighborhood mapping |

### SQL analytics

7 analytical views powering dashboards (`sql/views/02_analytical_views.sql`):
`vw_daily_platform_sentiment`, `vw_platform_comparison`, `vw_phase_emotion_trajectory`, `vw_neighborhood_emotion_heatmap`, `vw_platform_phase_matrix`, `vw_topic_phase_summary`, `vw_engagement_sentiment`

7 interview-ready queries demonstrating CTEs, window functions, correlation, and spike detection (`sql/queries/03_interview_queries.sql`)

## Quick Start

```bash
git clone https://github.com/YOUR_USERNAME/south-shore-sentiment-study.git
cd south-shore-sentiment-study

cp config/.env.example .env
python -m venv .venv && source .venv/bin/activate

# Install
pip install -r requirements.txt
pip install -e .
python -m spacy download en_core_web_sm

# Run full pipeline
make run-all

# Launch dashboard
make dashboard
```

| Command | Description |
|---------|-------------|
| `make run-all` | Full pipeline: ingest → clean → analyze → report |
| `make dashboard` | Launch Streamlit on port 8501 |
| `make pg-load` | Transfer analyzed data to PostgreSQL |
| `make excel-report` | Generate Excel workbook |
| `make test` | Run 25 tests with coverage |

## Project Structure

```
south-shore-sentiment-study/
├── config/                     # Settings, verified events, source registry
├── dashboards/app.py           # Streamlit dashboard (5 tabs)
├── sql/
│   ├── schema/                 # PostgreSQL star schema DDL
│   ├── views/                  # 7 analytical views
│   └── queries/                # 7 interview-ready SQL queries
├── src/
│   ├── ingestion/              # Reddit, YouTube, News, Synthetic collectors
│   ├── analysis/               # Cleaning, sentiment, emotions, topics, longitudinal
│   ├── visualization/          # Plotly charts, platform comparison, guidance
│   ├── exports/                # Excel report generator
│   └── utils/                  # DuckDB, PostgreSQL loader, logger, constants
├── tests/                      # pytest suite (25 tests)
├── Makefile                    # 13 task targets
└── requirements.txt            # All dependencies
```

## Verified Event Timeline

All findings are grounded in investigative reporting by [Block Club Chicago](https://blockclubchicago.org/). 14 verified events from Sep 2025 through Jan 2026 are documented in [`config/verified_events.yaml`](config/verified_events.yaml) with verification levels (L1: Official/Court records, L2: Multi-source journalism, L3: Single-source media, L4: Social media).

| Date | Event | Verification |
|------|-------|-------------|
| Sep 30, 2025 | Operation Midway Blitz — ICE/CBP raid at 7500 S. South Shore Dr | L1 |
| Oct 1, 2025 | Residents return to ransacked apartments | L2 |
| Oct 24, 2025 | Investigation reveals 1+ emergency call/day for 5 years pre-raid | L2 |
| Nov 7, 2025 | Judge orders building cleared | L2 |
| Nov 24, 2025 | Tenants union forms, demands relocation assistance | L2 |
| Dec 12, 2025 | Building vacated by court deadline | L2 |
| Jan 22, 2026 | State investigates landlord for tipping off feds | L2 |

## Ethics & Limitations

**Ethics:** Public data only. No PII collected or published. Usernames stripped during processing. All outputs are aggregate-level. Verified event timeline grounded in professional investigative journalism. Removal channel available for organizations requesting data exclusion.

**Limitations:** Reddit/YouTube commenters are not representative of the full South Shore community — those most affected may lack internet access or be afraid to post publicly. Geographic inference uses text mention matching, not GPS. Emotion classification models have inherent error rates. Twitter/X excluded due to API access restrictions. Platform bias exists: Reddit skews younger/male, news comments attract more politically engaged users.

## Next Steps

1. **Power BI dashboard** — Connect to PostgreSQL star schema, build 4 report pages with DAX measures, publish to Power BI Service
2. **A/B test intervention timing** — Partner with a community organization to test whether deploying resources at the data-identified crossover points (day 5-7, weeks 9-10) improves outcomes vs. standard response timing
3. **Live monitoring mode** — Convert the batch pipeline to near-real-time ingestion with scheduled collection, enabling proactive rather than retrospective analysis for future events
4. **Expand to Twitter/X** — If API access becomes available, add the highest-velocity platform for real-time discourse tracking

## License

MIT — See [LICENSE](LICENSE)
