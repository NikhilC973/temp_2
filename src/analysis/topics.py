"""BERTopic — Dynamic topic modeling with keyword fallback."""

import numpy as np

from src.utils.constants import PROJECT_ROOT
from src.utils.db import get_connection, init_database
from src.utils.logger import log

KEYWORD_TOPICS = {
    0: {
        "label": "Raid Operations",
        "kw": [
            "raid",
            "ice",
            "cbp",
            "agents",
            "tactical",
            "enforcement",
            "operation",
            "midway",
            "blitz",
        ],
    },
    1: {
        "label": "Helicopters & Flashbangs",
        "kw": ["helicopter", "flashbang", "loud", "noise", "swat", "breach"],
    },
    2: {
        "label": "Property Damage",
        "kw": ["damage", "door", "broken", "lock", "building", "apartment", "repair", "landlord"],
    },
    3: {
        "label": "Legal Aid & Rights",
        "kw": ["lawyer", "legal", "rights", "warrant", "know your rights", "attorney", "nijc"],
    },
    4: {
        "label": "Child & Family Trauma",
        "kw": ["child", "children", "kids", "school", "family", "nightmare", "trauma", "scared"],
    },
    5: {
        "label": "Community Organizing",
        "kw": ["organize", "march", "protest", "meeting", "rally", "community", "solidarity"],
    },
    6: {
        "label": "Mutual Aid & Resources",
        "kw": ["mutual aid", "fund", "donate", "resource", "hotline", "counseling", "support"],
    },
    7: {
        "label": "Political Response",
        "kw": [
            "mayor",
            "council",
            "elected",
            "officials",
            "sanctuary",
            "city",
            "policy",
            "government",
        ],
    },
    8: {
        "label": "Media Coverage",
        "kw": ["report", "coverage", "article", "news", "ap", "block club", "wbez", "media"],
    },
    9: {
        "label": "Housing & Displacement",
        "kw": ["housing", "displaced", "tenant", "eviction", "rent", "shelter"],
    },
}


def _fallback_topic(text: str) -> tuple:
    tl = (text or "").lower()
    best_id, best_score = -1, 0
    for tid, info in KEYWORD_TOPICS.items():
        score = sum(1 for k in info["kw"] if k in tl)
        if score > best_score:
            best_score, best_id = score, tid
    if best_id >= 0:
        i = KEYWORD_TOPICS[best_id]
        return best_id, min(best_score / 5, 1.0), i["kw"][:5], i["label"]
    return -1, 0.0, ["outlier"], "Outlier"


def run_topic_modeling(min_topic_size: int = 5, nr_topics: str = "auto"):
    log.info("Starting BERTopic topic modeling")
    init_database()
    conn = get_connection()
    df = conn.execute(
        "SELECT id, text_clean, phase, platform FROM posts_clean "
        "WHERE is_duplicate=false AND quality_flag='ok' AND word_count>=5"
    ).fetchdf()
    if df.empty:
        log.warning("No posts")
        conn.close()
        return

    try:
        from bertopic import BERTopic
        from sentence_transformers import SentenceTransformer

        model = BERTopic(
            embedding_model=SentenceTransformer("all-MiniLM-L6-v2"),
            min_topic_size=min_topic_size,
            verbose=True,
            calculate_probabilities=True,
        )
        topics, probs = model.fit_transform(df["text_clean"].tolist())
        df["topic_id"] = topics
        df["topic_prob"] = [
            float(p.max()) if isinstance(p, np.ndarray) else float(p) for p in probs
        ]
        term_map = {}
        for t in set(topics):
            if t == -1:
                term_map[-1] = ["outlier"]
                continue
            terms = model.get_topic(t)
            term_map[t] = [x[0] for x in terms[:10]] if terms else ["unknown"]
        df["top_terms"] = df["topic_id"].map(lambda t: term_map.get(t, []))
        df["topic_label"] = df["topic_id"].map(
            lambda t: f"Topic_{t}: {', '.join(term_map.get(t, [])[:3])}"
        )
        model.save(str(PROJECT_ROOT / "data/processed/bertopic_model"))
    except Exception as e:
        log.warning(f"BERTopic failed ({e}), using keyword fallback")
        results = df["text_clean"].apply(_fallback_topic)
        df["topic_id"] = results.apply(lambda x: x[0])
        df["topic_prob"] = results.apply(lambda x: x[1])
        df["top_terms"] = results.apply(lambda x: x[2])
        df["topic_label"] = results.apply(lambda x: x[3])

    conn.execute("DELETE FROM posts_topics")
    for _, r in df.iterrows():
        conn.execute(
            "INSERT INTO posts_topics VALUES (?,?,?,?,?)",
            [
                r["id"],
                int(r["topic_id"]),
                r["topic_label"],
                float(r["topic_prob"]),
                r["top_terms"] if isinstance(r["top_terms"], list) else [],
            ],
        )

    out = PROJECT_ROOT / "data/processed"
    out.mkdir(parents=True, exist_ok=True)
    df[["id", "topic_id", "topic_label", "topic_prob", "top_terms"]].to_parquet(
        out / "topics.parquet", index=False
    )
    log.info(f"Topic modeling complete: {df['topic_label'].value_counts().head(5).to_dict()}")
    conn.close()


if __name__ == "__main__":
    run_topic_modeling()
