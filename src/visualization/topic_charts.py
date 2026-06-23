"""Topic visualization charts."""

import pandas as pd
import plotly.graph_objects as go

from src.visualization.chart_style import apply_dark_layout


def create_topic_distribution_chart(topic_df: pd.DataFrame) -> go.Figure:
    # Exclude the BERTopic outlier bucket (-1) so real topics are visible
    filtered = topic_df[~topic_df["topic_label"].str.contains("outlier", case=False, na=False)]
    counts = filtered["topic_label"].value_counts().head(15)
    fig = go.Figure(
        go.Bar(x=counts.values, y=counts.index, orientation="h", marker_color="#4C78A8")
    )
    fig.update_layout(
        title="Top 15 Discussion Topics",
        height=500,
        xaxis_title="Number of Posts",
        yaxis=dict(autorange="reversed"),
    )
    return apply_dark_layout(fig)


def create_topic_phase_heatmap(df: pd.DataFrame) -> go.Figure:
    if "phase" not in df.columns or "topic_label" not in df.columns:
        return apply_dark_layout(go.Figure())
    df = df[~df["topic_label"].str.contains("outlier", case=False, na=False)]
    ct = pd.crosstab(df["topic_label"], df["phase"], normalize="columns")
    top_topics = ct.sum(axis=1).nlargest(10).index
    ct = ct.loc[ct.index.isin(top_topics)]

    fig = go.Figure(
        data=go.Heatmap(
            z=ct.values,
            x=ct.columns,
            y=ct.index,
            colorscale="Blues",
            colorbar=dict(title="Share"),
        )
    )
    fig.update_layout(title="Topic Prevalence by Phase", height=450)
    return apply_dark_layout(fig)
