"""
Longitudinal Analysis — Emotion trajectories over time with bootstrapped CIs.

Computes daily/phase-level emotion means, confidence intervals, and
platform contrasts for the visualization layer.
"""

import numpy as np
import pandas as pd

from src.utils.constants import PHASES, PROJECT_ROOT, TARGET_EMOTIONS
from src.utils.db import get_connection
from src.utils.logger import log


def bootstrap_ci(values: np.ndarray, n_iterations: int = 1000, ci: float = 0.95) -> tuple:
    """Compute bootstrapped confidence interval for mean."""
    if len(values) < 2:
        m = float(np.mean(values)) if len(values) > 0 else 0.0
        return m, m, m

    rng = np.random.default_rng(42)
    means = []
    for _ in range(n_iterations):
        sample = rng.choice(values, size=len(values), replace=True)
        means.append(np.mean(sample))

    means = sorted(means)
    alpha = (1 - ci) / 2
    lo = means[int(alpha * len(means))]
    hi = means[int((1 - alpha) * len(means))]
    return float(np.mean(values)), float(lo), float(hi)


def compute_phase_emotions(df: pd.DataFrame) -> pd.DataFrame:
    """Compute mean emotion scores per phase with CIs."""
    rows = []
    for phase in PHASES:
        phase_df = df[df["phase"] == phase]
        if phase_df.empty:
            continue

        row = {"phase": phase, "label": PHASES[phase]["label"], "n_posts": len(phase_df)}
        for emo in TARGET_EMOTIONS:
            col = f"emo_{emo}"
            if col in phase_df.columns:
                vals = phase_df[col].dropna().values
                mean, lo, hi = bootstrap_ci(vals)
                row[f"{emo}_mean"] = mean
                row[f"{emo}_ci_lo"] = lo
                row[f"{emo}_ci_hi"] = hi
        rows.append(row)

    return pd.DataFrame(rows)


def compute_daily_emotions(df: pd.DataFrame) -> pd.DataFrame:
    """Compute daily mean emotion scores."""
    df = df.copy()
    df["date"] = pd.to_datetime(df["dt_utc"]).dt.date

    rows = []
    for date, group in df.groupby("date"):
        row = {"date": date, "n_posts": len(group)}
        for emo in TARGET_EMOTIONS:
            col = f"emo_{emo}"
            if col in group.columns:
                row[f"{emo}_mean"] = group[col].mean()
        # Sentiment
        if "vader_compound" in group.columns:
            row["vader_mean"] = group["vader_compound"].mean()
        rows.append(row)

    return pd.DataFrame(rows).sort_values("date")


def compute_platform_contrast(df: pd.DataFrame) -> pd.DataFrame:
    """Compare emotion distributions across platforms."""
    rows = []
    for platform in df["platform"].unique():
        plat_df = df[df["platform"] == platform]
        row = {"platform": platform, "n_posts": len(plat_df)}
        for emo in TARGET_EMOTIONS:
            col = f"emo_{emo}"
            if col in plat_df.columns:
                row[f"{emo}_mean"] = plat_df[col].mean()
        if "vader_compound" in plat_df.columns:
            row["vader_mean"] = plat_df["vader_compound"].mean()
        rows.append(row)
    return pd.DataFrame(rows)


def compute_geo_emotions(df: pd.DataFrame) -> pd.DataFrame:
    """Compute emotion scores by neighborhood."""
    rows = []
    # Explode neighborhoods for per-neighborhood analysis
    geo_df = df[df["has_geo"]].copy()
    if "neighborhoods" in geo_df.columns:
        geo_df = geo_df.explode("neighborhoods")
        for hood, group in geo_df.groupby("neighborhoods"):
            row = {"neighborhood": hood, "n_posts": len(group)}
            for emo in TARGET_EMOTIONS:
                col = f"emo_{emo}"
                if col in group.columns:
                    row[f"{emo}_mean"] = group[col].mean()
            rows.append(row)
    return pd.DataFrame(rows)


def run_longitudinal_analysis():
    """Run full longitudinal analysis and export results."""
    log.info("📈 Running longitudinal analysis")

    conn = get_connection()
    df = conn.execute("SELECT * FROM posts_full").fetchdf()
    conn.close()

    if df.empty:
        log.warning("No data for longitudinal analysis")
        return

    log.info(f"Analyzing {len(df)} posts")

    # Compute all aggregations
    phase_df = compute_phase_emotions(df)
    daily_df = compute_daily_emotions(df)
    platform_df = compute_platform_contrast(df)
    geo_df = compute_geo_emotions(df)

    # Export
    out_dir = PROJECT_ROOT / "data" / "exports"
    out_dir.mkdir(parents=True, exist_ok=True)

    phase_df.to_parquet(out_dir / "phase_emotions.parquet", index=False)
    daily_df.to_parquet(out_dir / "daily_emotions.parquet", index=False)
    platform_df.to_parquet(out_dir / "platform_contrast.parquet", index=False)
    geo_df.to_parquet(out_dir / "geo_emotions.parquet", index=False)

    # Also CSV for easy sharing
    phase_df.to_csv(out_dir / "phase_emotions.csv", index=False)
    daily_df.to_csv(out_dir / "daily_emotions.csv", index=False)

    log.info(f"✅ Longitudinal analysis complete. Exports in {out_dir}")
    log.info(f"   Phase summary:\n{phase_df[['phase', 'n_posts']].to_string()}")

    return {"phase": phase_df, "daily": daily_df, "platform": platform_df, "geo": geo_df}


if __name__ == "__main__":
    run_longitudinal_analysis()
