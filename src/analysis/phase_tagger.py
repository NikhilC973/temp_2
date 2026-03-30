"""Phase tagging — assigns temporal phases. Already done in cleaning; standalone re-run."""

import pandas as pd

from src.utils.constants import PHASES
from src.utils.db import get_connection
from src.utils.logger import log


def run_phase_tagging():
    log.info("Running phase tagging pass")
    conn = get_connection()
    df = conn.execute("SELECT id, dt_utc FROM posts_clean").fetchdf()
    if df.empty:
        conn.close()
        return

    for _, row in df.iterrows():
        try:
            dt = pd.Timestamp(row["dt_utc"])
            date_str = dt.strftime("%Y-%m-%d")
            phase = "out_of_window"
            for pname, pinfo in PHASES.items():
                if pinfo["start"] <= date_str <= pinfo["end"]:
                    phase = pname
                    break
            conn.execute("UPDATE posts_clean SET phase=? WHERE id=?", [phase, row["id"]])
        except Exception:
            pass

    dist = conn.execute("SELECT phase, COUNT(*) as n FROM posts_clean GROUP BY phase").fetchdf()
    log.info(f"Phase distribution:\n{dist.to_string()}")
    conn.close()


if __name__ == "__main__":
    run_phase_tagging()
