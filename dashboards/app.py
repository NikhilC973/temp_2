"""
South Shore Sentiment Study — Interactive Streamlit Dashboard
Tabs: Overview | Themes | Geography | Methodology | Program Guidance
"""

import sys
from pathlib import Path

import pandas as pd
import streamlit as st

# Add project root to Python path so src imports work
PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from src.utils.constants import PHASES
from src.visualization.emotion_curves import (
    create_emotion_trajectory_chart,
    create_phase_comparison_chart,
    create_platform_contrast_chart,
    create_sentiment_heatmap,
)
from src.visualization.geo_charts import create_geo_fear_timeline, create_neighborhood_chart
from src.visualization.topic_charts import create_topic_distribution_chart

st.set_page_config(page_title="South Shore Sentiment Study", page_icon="🏘️", layout="wide")

# Light version of UI padding only
st.markdown(
    """
    <style>
      .block-container { padding-top: 2.5rem; }
    </style>
    """,
    unsafe_allow_html=True,
)


@st.cache_data
def load_data():
    d = {}
    exp = PROJECT_ROOT / "data/exports"
    pro = PROJECT_ROOT / "data/processed"

    for name, path in [
        ("phase", exp / "phase_emotions.parquet"),
        ("daily", exp / "daily_emotions.parquet"),
        ("platform", exp / "platform_contrast.parquet"),
        ("geo", exp / "geo_emotions.parquet"),
        ("topics", pro / "topics.parquet"),
    ]:
        try:
            d[name] = pd.read_parquet(path)
        except Exception:
            d[name] = pd.DataFrame()

    try:
        from src.utils.db import query_df

        d["full"] = query_df("SELECT * FROM posts_full")
    except Exception:
        d["full"] = pd.DataFrame()

    return d


data = load_data()

with st.sidebar:
    st.title("🏘️ South Shore Sentiment Study")
    st.markdown("---")
    st.markdown("**Event:** ICE/CBP Raid, Sep 30 2025")
    st.markdown("**Location:** South Shore, Chicago")
    st.markdown("---")

    selected_phases = st.multiselect(
        "Phases",
        options=list(PHASES.keys()),
        default=list(PHASES.keys()),
        format_func=lambda x: PHASES[x]["label"],
    )

    all_emotions = ["fear", "anger", "joy", "gratitude", "sadness", "pride"]
    selected_emotions = st.multiselect(
        "Emotions",
        options=all_emotions,
        default=all_emotions,
        format_func=lambda x: x.capitalize(),
    )

    st.markdown("---")
    if not data["phase"].empty:
        st.download_button("📥 Phase Data", data["phase"].to_csv(index=False), "phase_emotions.csv")

tab1, tab2, tab3, tab4, tab5 = st.tabs(
    ["📈 Overview", "🔍 Themes", "🗺️ Geography", "📋 Methodology", "🎯 Guidance"]
)

with tab1:
    st.header("Emotion Trajectory Overview")

    phase_filtered = pd.DataFrame()
    if not data["phase"].empty:
        phase_filtered = data["phase"][data["phase"]["phase"].isin(selected_phases)].copy()

        cols = st.columns(min(len(selected_phases), 7) if selected_phases else 1)
        for i, p in enumerate(selected_phases):
            info = PHASES[p]
            r = phase_filtered[phase_filtered["phase"] == p]
            if not r.empty and "n_posts" in r.columns:
                cols[i % len(cols)].metric(info["label"], f"{int(r['n_posts'].iloc[0])} posts")
            else:
                cols[i % len(cols)].metric(info["label"], "0 posts")

    if not data["daily"].empty:
        fig = create_emotion_trajectory_chart(data["daily"], selected_emotions=selected_emotions)
        st.plotly_chart(fig, theme=None, width="stretch")

    c1, c2 = st.columns(2)
    with c1:
        if not phase_filtered.empty:
            fig = create_phase_comparison_chart(phase_filtered)
            st.plotly_chart(fig, theme=None, width="stretch")

    with c2:
        if not data["platform"].empty:
            fig = create_platform_contrast_chart(data["platform"])
            st.plotly_chart(fig, theme=None, width="stretch")

    if not data["daily"].empty:
        fig = create_sentiment_heatmap(data["daily"])
        st.plotly_chart(fig, theme=None, width="stretch")

with tab2:
    st.header("Discussion Themes")
    if not data["topics"].empty:
        st.plotly_chart(
            create_topic_distribution_chart(data["topics"]), theme=None, width="stretch"
        )

        sel = st.selectbox("Explore topic", sorted(data["topics"]["topic_label"].unique()))
        tp = data["topics"][data["topics"]["topic_label"] == sel]
        st.write(f"**{len(tp)} posts**")
        if not tp.empty and isinstance(tp["top_terms"].iloc[0], list):
            st.write(f"Top terms: {', '.join(tp['top_terms'].iloc[0][:10])}")
    else:
        st.info("Run `make analyze`")

with tab3:
    st.header("Neighborhood Analysis")
    st.warning("⚠️ Geo from text mentions, not GPS. Interpret with caution.")
    if not data["geo"].empty:
        st.plotly_chart(create_neighborhood_chart(data["geo"]), theme=None, width="stretch")

    if not data["full"].empty:
        fig = create_geo_fear_timeline(data["full"])
        if fig.data:
            st.plotly_chart(fig, theme=None, width="stretch")

with tab4:
    st.header("Methodology & Ethics")
    st.markdown(
        """
**Sources:** 14 subreddits + 5 news sites + YouTube Data API v3 | **Window:** Sep 16 – Dec 12, 2025 (7 phases) | **NLP:** VADER + RoBERTa + GoEmotions + BERTopic

**Verification:** L1 Official/FOIA → L2 Two-Source Media → L3 Single-Source → L4 Social

**Ethics:** Public data only • No PII • Aggregate outputs • Removal channel available • Community-first orientation

**Limitations:** Selection bias (Reddit ≠ all residents) • Platform bias • Geo-inference from text • Model uncertainty • Twitter/X excluded
"""
    )

with tab5:
    st.header("Actionable Recommendations")
    st.dataframe(
        pd.DataFrame(
            {
                "Window": [
                    "0–24h",
                    "Days 2–5",
                    "Days 5–14",
                    "Weeks 3–5",
                    "Weeks 6–8",
                    "Weeks 9–10",
                ],
                "Priority": [
                    "Crisis comms; know-your-rights; hotlines",
                    "Legal aid; trauma counseling; damage docs",
                    "Mutual aid; school support; organizing",
                    "Case management; policy advocacy; infrastructure",
                    "Tenant union support; housing advocacy; court monitoring",
                    "Emergency relocation; housing navigation; homelessness prevention",
                ],
                "Emotion": [
                    "Fear + confusion peak",
                    "Anger + organizing",
                    "Solidarity + gratitude",
                    "Pride + resilience",
                    "Anger resurgence + sadness",
                    "Sadness + fear resurgence",
                ],
                "Priority Level": [
                    "🔴 CRITICAL",
                    "🟠 HIGH",
                    "🟠 HIGH",
                    "🟡 MEDIUM",
                    "🟠 HIGH",
                    "🔴 CRITICAL",
                ],
            }
        ),
        width="stretch",
        hide_index=True,
    )
    st.success(
        "**Critical windows: Days 2–7 and Weeks 9–10.** "
        "Fear transforms to organized anger in Week 1 — deploy resources here. "
        "Second crisis emerges during displacement phase as housing insecurity triggers re-traumatization."
    )
