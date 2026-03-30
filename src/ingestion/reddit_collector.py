"""
Reddit Data Collector — No Official API Required

Strategy (elite approach after API rejection):
1. PRIMARY:   PullPush.io (Pushshift successor) — historical search
2. FALLBACK:  Old Reddit JSON endpoints (.json suffix)
3. BULK:      Arctic Shift data dumps (for backfill)

All methods use public, legal access points with respectful rate limiting.
"""

import hashlib
import json
import time
from datetime import datetime, timezone
from typing import Generator

import requests

from src.utils.constants import (
    COLLECTION_START,
    EXTENDED_END,
    SEARCH_TERMS,
    SUBREDDITS,
)
from src.utils.logger import log


# ── Rate Limiter ─────────────────────────────────────────
class RateLimiter:
    """Simple rate limiter with configurable delay."""

    def __init__(self, min_delay: float = 2.0):
        self.min_delay = min_delay
        self._last_request = 0.0

    def wait(self):
        elapsed = time.time() - self._last_request
        if elapsed < self.min_delay:
            sleep_time = self.min_delay - elapsed
            time.sleep(sleep_time)
        self._last_request = time.time()


# ── PullPush.io Collector ────────────────────────────────
class PullPushCollector:
    """
    Collect Reddit data via PullPush.io (Pushshift successor).
    Endpoints:
      - /reddit/search/submission/  (posts)
      - /reddit/search/comment/     (comments)
    """

    BASE_URL = "https://api.pullpush.io/reddit"
    HEADERS = {
        "User-Agent": "SouthShoreSentimentStudy/1.0 (Academic Research; Contact: study@example.com)"
    }

    def __init__(self, rate_limit: float = 2.0):
        self.limiter = RateLimiter(rate_limit)
        self.session = requests.Session()
        self.session.headers.update(self.HEADERS)

    def search_submissions(
        self,
        query: str,
        subreddit: str | None = None,
        after_epoch: int | None = None,
        before_epoch: int | None = None,
        size: int = 100,
    ) -> list[dict]:
        """Search Reddit submissions via PullPush."""
        self.limiter.wait()

        params = {
            "q": query,
            "size": min(size, 100),
            "sort": "desc",
            "sort_type": "created_utc",
        }
        if subreddit:
            params["subreddit"] = subreddit
        if after_epoch:
            params["after"] = after_epoch
        if before_epoch:
            params["before"] = before_epoch

        try:
            resp = self.session.get(
                f"{self.BASE_URL}/search/submission/",
                params=params,
                timeout=30,
            )
            resp.raise_for_status()
            data = resp.json().get("data", [])
            log.info(f"PullPush submissions: q='{query}' sub={subreddit} → {len(data)} results")
            return data
        except requests.RequestException as e:
            log.warning(f"PullPush submission error: {e}")
            return []

    def search_comments(
        self,
        query: str,
        subreddit: str | None = None,
        after_epoch: int | None = None,
        before_epoch: int | None = None,
        size: int = 100,
    ) -> list[dict]:
        """Search Reddit comments via PullPush."""
        self.limiter.wait()

        params = {
            "q": query,
            "size": min(size, 100),
            "sort": "desc",
            "sort_type": "created_utc",
        }
        if subreddit:
            params["subreddit"] = subreddit
        if after_epoch:
            params["after"] = after_epoch
        if before_epoch:
            params["before"] = before_epoch

        try:
            resp = self.session.get(
                f"{self.BASE_URL}/search/comment/",
                params=params,
                timeout=30,
            )
            resp.raise_for_status()
            data = resp.json().get("data", [])
            log.info(f"PullPush comments: q='{query}' sub={subreddit} → {len(data)} results")
            return data
        except requests.RequestException as e:
            log.warning(f"PullPush comment error: {e}")
            return []

    def _normalize_submission(self, item: dict) -> dict:
        """Normalize a PullPush submission to our schema."""
        created_utc = item.get("created_utc", 0)
        dt = datetime.fromtimestamp(created_utc, tz=timezone.utc)

        text = item.get("selftext", "") or ""
        title = item.get("title", "") or ""
        full_text = f"{title} {text}".strip()

        post_id = f"reddit_sub_{item.get('id', hashlib.md5(full_text.encode()).hexdigest()[:12])}"

        return {
            "id": post_id,
            "platform": "reddit",
            "source": item.get("subreddit", "unknown"),
            "url": f"https://reddit.com{item.get('permalink', '')}",
            "dt_utc": dt.isoformat(),
            "text": full_text,
            "title": title,
            "author_display": item.get("author", "[deleted]"),
            "score": item.get("score", 0),
            "like_count": item.get("score", 0),
            "reply_count": item.get("num_comments", 0),
            "share_count": 0,
            "parent_id": None,
            "post_type": "submission",
            "search_term": None,  # set by caller
        }

    def _normalize_comment(self, item: dict) -> dict:
        """Normalize a PullPush comment to our schema."""
        created_utc = item.get("created_utc", 0)
        dt = datetime.fromtimestamp(created_utc, tz=timezone.utc)

        text = item.get("body", "") or ""
        post_id = f"reddit_com_{item.get('id', hashlib.md5(text.encode()).hexdigest()[:12])}"

        return {
            "id": post_id,
            "platform": "reddit",
            "source": item.get("subreddit", "unknown"),
            "url": f"https://reddit.com{item.get('permalink', '')}",
            "dt_utc": dt.isoformat(),
            "text": text,
            "title": None,
            "author_display": item.get("author", "[deleted]"),
            "score": item.get("score", 0),
            "like_count": item.get("score", 0),
            "reply_count": 0,
            "share_count": 0,
            "parent_id": item.get("parent_id"),
            "post_type": "comment",
            "search_term": None,
        }

    def collect_all(
        self,
        subreddits: list[str] | None = None,
        search_terms: list[str] | None = None,
        after_dt: datetime | None = None,
        before_dt: datetime | None = None,
    ) -> Generator[dict, None, None]:
        """
        Collect all submissions + comments matching our queries.
        Yields normalized post dicts.
        """
        subs = subreddits or SUBREDDITS
        terms = search_terms or SEARCH_TERMS
        after_epoch = int(after_dt.timestamp()) if after_dt else int(COLLECTION_START.timestamp())
        before_epoch = int(before_dt.timestamp()) if before_dt else int(EXTENDED_END.timestamp())

        seen_ids = set()

        for term in terms:
            # Search across all subreddits
            for sub in subs:
                # Submissions
                for item in self.search_submissions(
                    query=term,
                    subreddit=sub,
                    after_epoch=after_epoch,
                    before_epoch=before_epoch,
                    size=100,
                ):
                    normalized = self._normalize_submission(item)
                    normalized["search_term"] = term
                    if normalized["id"] not in seen_ids:
                        seen_ids.add(normalized["id"])
                        yield normalized

                # Comments
                for item in self.search_comments(
                    query=term,
                    subreddit=sub,
                    after_epoch=after_epoch,
                    before_epoch=before_epoch,
                    size=100,
                ):
                    normalized = self._normalize_comment(item)
                    normalized["search_term"] = term
                    if normalized["id"] not in seen_ids:
                        seen_ids.add(normalized["id"])
                        yield normalized

            # Also search without subreddit filter (broader sweep)
            for item in self.search_submissions(
                query=term,
                subreddit=None,
                after_epoch=after_epoch,
                before_epoch=before_epoch,
                size=100,
            ):
                normalized = self._normalize_submission(item)
                normalized["search_term"] = term
                if normalized["id"] not in seen_ids:
                    seen_ids.add(normalized["id"])
                    yield normalized

        log.info(f"PullPush collection complete: {len(seen_ids)} unique posts")


# ── Old Reddit JSON Collector (Fallback) ─────────────────
class OldRedditCollector:
    """
    Fallback collector using Old Reddit's JSON interface.
    Append .json to any Reddit URL for structured data.

    Limitations: Only recent/current posts, no deep historical search.
    Use for: supplementing PullPush gaps and getting fresh data.
    """

    BASE_URL = "https://old.reddit.com"
    HEADERS = {"User-Agent": "SouthShoreSentimentStudy/1.0 (Academic Research)"}

    def __init__(self, rate_limit: float = 2.5):
        self.limiter = RateLimiter(rate_limit)
        self.session = requests.Session()
        self.session.headers.update(self.HEADERS)

    def search_subreddit(self, subreddit: str, query: str, limit: int = 25) -> list[dict]:
        """Search a subreddit using old.reddit.com JSON."""
        self.limiter.wait()

        url = f"{self.BASE_URL}/r/{subreddit}/search.json"
        params = {
            "q": query,
            "restrict_sr": "on",
            "sort": "relevance",
            "t": "month",
            "limit": min(limit, 100),
        }

        try:
            resp = self.session.get(url, params=params, timeout=30)
            resp.raise_for_status()
            data = resp.json()
            children = data.get("data", {}).get("children", [])
            log.info(f"OldReddit search: r/{subreddit} q='{query}' → {len(children)} results")
            return [c["data"] for c in children if c.get("kind") == "t3"]
        except requests.RequestException as e:
            log.warning(f"OldReddit error for r/{subreddit}: {e}")
            return []

    def get_post_comments(self, permalink: str, limit: int = 50) -> list[dict]:
        """Get comments for a specific post via JSON."""
        self.limiter.wait()

        url = f"{self.BASE_URL}{permalink}.json"
        params = {"limit": limit, "sort": "best"}

        try:
            resp = self.session.get(url, params=params, timeout=30)
            resp.raise_for_status()
            data = resp.json()

            comments = []
            if len(data) > 1:
                self._extract_comments(data[1].get("data", {}).get("children", []), comments)
            return comments
        except requests.RequestException as e:
            log.warning(f"OldReddit comments error: {e}")
            return []

    def _extract_comments(self, children: list, result: list, depth: int = 0):
        """Recursively extract comments from Reddit JSON tree."""
        for child in children:
            if child.get("kind") != "t1":
                continue
            data = child.get("data", {})
            if data.get("body") and data["body"] != "[deleted]":
                result.append(data)
            # Recurse into replies
            replies = data.get("replies")
            if isinstance(replies, dict):
                reply_children = replies.get("data", {}).get("children", [])
                if depth < 3:  # limit recursion depth
                    self._extract_comments(reply_children, result, depth + 1)

    def _normalize(self, item: dict, subreddit: str, search_term: str) -> dict:
        """Normalize Old Reddit JSON item."""
        created_utc = item.get("created_utc", 0)
        dt = datetime.fromtimestamp(created_utc, tz=timezone.utc)
        is_comment = "body" in item

        text = (
            item.get("body", "")
            if is_comment
            else f"{item.get('title', '')} {item.get('selftext', '')}".strip()
        )
        post_id = f"reddit_{'com' if is_comment else 'sub'}_{item.get('id', 'unknown')}"

        return {
            "id": post_id,
            "platform": "reddit",
            "source": subreddit,
            "url": f"https://reddit.com{item.get('permalink', '')}",
            "dt_utc": dt.isoformat(),
            "text": text,
            "title": None if is_comment else item.get("title"),
            "author_display": item.get("author", "[deleted]"),
            "score": item.get("score", 0),
            "like_count": item.get("ups", 0),
            "reply_count": item.get("num_comments", 0) if not is_comment else 0,
            "share_count": 0,
            "parent_id": item.get("parent_id") if is_comment else None,
            "post_type": "comment" if is_comment else "submission",
            "search_term": search_term,
        }

    def collect_all(
        self,
        subreddits: list[str] | None = None,
        search_terms: list[str] | None = None,
    ) -> Generator[dict, None, None]:
        """Collect from all subreddits using Old Reddit JSON."""
        subs = subreddits or SUBREDDITS
        terms = search_terms or SEARCH_TERMS
        seen_ids = set()

        for sub in subs:
            for term in terms:
                # Get submissions
                submissions = self.search_subreddit(sub, term)
                for item in submissions:
                    normalized = self._normalize(item, sub, term)
                    if normalized["id"] not in seen_ids and normalized["text"].strip():
                        seen_ids.add(normalized["id"])
                        yield normalized

                    # Also get comments on matching posts
                    permalink = item.get("permalink")
                    if permalink and item.get("num_comments", 0) > 0:
                        comments = self.get_post_comments(permalink, limit=30)
                        for comment in comments:
                            cn = self._normalize(comment, sub, term)
                            if cn["id"] not in seen_ids and cn["text"].strip():
                                seen_ids.add(cn["id"])
                                yield cn

        log.info(f"OldReddit collection complete: {len(seen_ids)} unique posts")


# ── Convenience ──────────────────────────────────────────
def collect_reddit_data(
    method: str = "pullpush",
    subreddits: list[str] | None = None,
    search_terms: list[str] | None = None,
) -> list[dict]:
    """
    High-level function to collect Reddit data.

    Args:
        method: 'pullpush' | 'old_reddit' | 'both'
    """
    results = []
    seen = set()

    if method in ("pullpush", "both"):
        collector = PullPushCollector()
        for post in collector.collect_all(subreddits, search_terms):
            if post["id"] not in seen:
                seen.add(post["id"])
                results.append(post)

    if method in ("old_reddit", "both"):
        collector = OldRedditCollector()
        for post in collector.collect_all(subreddits, search_terms):
            if post["id"] not in seen:
                seen.add(post["id"])
                results.append(post)

    log.info(f"Total Reddit posts collected ({method}): {len(results)}")
    return results


if __name__ == "__main__":
    posts = collect_reddit_data(method="both")
    print(f"Collected {len(posts)} posts")
    if posts:
        print(f"Sample: {json.dumps(posts[0], indent=2, default=str)}")
