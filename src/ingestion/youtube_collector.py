"""
YouTube Data Collector — YouTube Data API v3 integration.

Collects public video metadata, statistics, and comment threads for
South Shore ICE raid discourse analysis.

Requires: google-api-python-client (pip install google-api-python-client)
API Key: Set YOUTUBE_API_KEY environment variable.
Free tier: 10,000 quota units/day.
"""

import hashlib
import os
import time
from datetime import datetime, timezone

from src.utils.constants import (
    COLLECTION_START,
    EXTENDED_END,
    YOUTUBE_SEARCH_TERMS,
)
from src.utils.logger import log


class RateLimiter:
    """Simple rate limiter with configurable delay."""

    def __init__(self, min_delay: float = 0.5):
        self.min_delay = min_delay
        self._last_request = 0.0

    def wait(self):
        elapsed = time.time() - self._last_request
        if elapsed < self.min_delay:
            time.sleep(self.min_delay - elapsed)
        self._last_request = time.time()


class YouTubeCollector:
    """
    Collect YouTube video metadata and comments via Data API v3.

    Quota costs (free tier = 10,000 units/day):
      - search.list:         100 units per call
      - videos.list:           1 unit per call (up to 50 IDs)
      - commentThreads.list:   1 unit per call
    """

    def __init__(self, api_key: str | None = None, rate_limit: float = 0.5):
        self.api_key = api_key or os.environ.get("YOUTUBE_API_KEY")
        self.limiter = RateLimiter(rate_limit)
        self._youtube = None
        self._quota_used = 0

    @property
    def youtube(self):
        """Lazy-load the YouTube API client."""
        if self._youtube is None:
            if not self.api_key:
                raise ValueError(
                    "YOUTUBE_API_KEY not set. Get one at "
                    "https://console.cloud.google.com/apis/credentials"
                )
            try:
                from googleapiclient.discovery import build

                self._youtube = build("youtube", "v3", developerKey=self.api_key)
                log.info("YouTube Data API v3 client initialized")
            except ImportError:
                raise ImportError(
                    "google-api-python-client required. Install: "
                    "pip install google-api-python-client"
                )
        return self._youtube

    def _track_quota(self, cost: int):
        """Track API quota usage."""
        self._quota_used += cost
        if self._quota_used > 9000:
            log.warning(f"YouTube quota usage high: {self._quota_used}/10000 units")

    def search_videos(
        self,
        query: str,
        max_results: int = 25,
        published_after: datetime | None = None,
        published_before: datetime | None = None,
    ) -> list[dict]:
        """Search for YouTube videos matching query."""
        self.limiter.wait()

        after = (published_after or COLLECTION_START).strftime("%Y-%m-%dT%H:%M:%SZ")
        before = (published_before or EXTENDED_END).strftime("%Y-%m-%dT%H:%M:%SZ")

        try:
            request = self.youtube.search().list(
                part="snippet",
                q=query,
                type="video",
                maxResults=min(max_results, 50),
                publishedAfter=after,
                publishedBefore=before,
                order="relevance",
                relevanceLanguage="en",
            )
            response = request.execute()
            self._track_quota(100)

            items = response.get("items", [])
            log.info(f"YouTube search: q='{query}' → {len(items)} videos")
            return items

        except Exception as e:
            log.warning(f"YouTube search error for '{query}': {e}")
            return []

    def get_video_details(self, video_ids: list[str]) -> list[dict]:
        """Batch-fetch video statistics and metadata (up to 50 per call)."""
        if not video_ids:
            return []

        self.limiter.wait()
        all_items = []

        # Process in batches of 50
        for i in range(0, len(video_ids), 50):
            batch = video_ids[i : i + 50]
            try:
                request = self.youtube.videos().list(
                    part="snippet,statistics,contentDetails",
                    id=",".join(batch),
                )
                response = request.execute()
                self._track_quota(1)
                all_items.extend(response.get("items", []))
            except Exception as e:
                log.warning(f"YouTube video details error: {e}")

        return all_items

    def get_video_comments(self, video_id: str, max_comments: int = 100) -> list[dict]:
        """Get comment threads for a video."""
        comments = []
        page_token = None

        while len(comments) < max_comments:
            self.limiter.wait()
            try:
                request = self.youtube.commentThreads().list(
                    part="snippet,replies",
                    videoId=video_id,
                    maxResults=min(100, max_comments - len(comments)),
                    order="relevance",
                    textFormat="plainText",
                    pageToken=page_token,
                )
                response = request.execute()
                self._track_quota(1)

                for item in response.get("items", []):
                    # Top-level comment
                    top = item["snippet"]["topLevelComment"]["snippet"]
                    comments.append(
                        {
                            "id": item["snippet"]["topLevelComment"]["id"],
                            "text": top.get("textDisplay", ""),
                            "author": top.get("authorDisplayName", ""),
                            "published_at": top.get("publishedAt", ""),
                            "like_count": top.get("likeCount", 0),
                            "reply_count": item["snippet"].get("totalReplyCount", 0),
                            "parent_id": video_id,
                            "is_reply": False,
                        }
                    )

                    # Replies (if included)
                    for reply in (item.get("replies") or {}).get("comments", []):
                        rs = reply["snippet"]
                        comments.append(
                            {
                                "id": reply["id"],
                                "text": rs.get("textDisplay", ""),
                                "author": rs.get("authorDisplayName", ""),
                                "published_at": rs.get("publishedAt", ""),
                                "like_count": rs.get("likeCount", 0),
                                "reply_count": 0,
                                "parent_id": item["snippet"]["topLevelComment"]["id"],
                                "is_reply": True,
                            }
                        )

                page_token = response.get("nextPageToken")
                if not page_token:
                    break

            except Exception as e:
                error_str = str(e)
                if "commentsDisabled" in error_str or "403" in error_str:
                    log.info(f"Comments disabled for video {video_id}")
                else:
                    log.warning(f"YouTube comments error for {video_id}: {e}")
                break

        return comments

    def _normalize_video(self, video: dict, search_term: str | None = None) -> dict:
        """Normalize a YouTube video to posts_raw schema."""
        snippet = video.get("snippet", {})
        stats = video.get("statistics", {})
        video_id = video.get("id", "")

        # Handle search result format vs video detail format
        if isinstance(video_id, dict):
            video_id = video_id.get("videoId", "")

        title = snippet.get("title", "")
        description = snippet.get("description", "")
        text = f"{title}. {description}".strip(". ")

        published = snippet.get("publishedAt", "")
        try:
            dt = datetime.fromisoformat(published.replace("Z", "+00:00"))
        except (ValueError, AttributeError):
            dt = datetime.now(timezone.utc)

        return {
            "id": f"yt_vid_{video_id}",
            "platform": "youtube",
            "source": snippet.get("channelTitle", "unknown"),
            "url": f"https://www.youtube.com/watch?v={video_id}",
            "dt_utc": dt.isoformat(),
            "text": text,
            "title": title,
            "author_display": snippet.get("channelTitle", ""),
            "score": int(stats.get("viewCount", 0)),
            "like_count": int(stats.get("likeCount", 0)),
            "reply_count": int(stats.get("commentCount", 0)),
            "share_count": 0,
            "parent_id": None,
            "post_type": "video",
            "search_term": search_term,
        }

    def _normalize_comment(
        self, comment: dict, video_url: str, channel: str, search_term: str | None = None
    ) -> dict:
        """Normalize a YouTube comment to posts_raw schema."""
        comment_id = comment["id"]

        published = comment.get("published_at", "")
        try:
            dt = datetime.fromisoformat(published.replace("Z", "+00:00"))
        except (ValueError, AttributeError):
            dt = datetime.now(timezone.utc)

        post_type = "reply" if comment.get("is_reply") else "comment"

        return {
            "id": f"yt_com_{comment_id}",
            "platform": "youtube",
            "source": channel,
            "url": f"{video_url}&lc={comment_id}",
            "dt_utc": dt.isoformat(),
            "text": comment.get("text", ""),
            "title": None,
            "author_display": comment.get("author", ""),
            "score": comment.get("like_count", 0),
            "like_count": comment.get("like_count", 0),
            "reply_count": comment.get("reply_count", 0),
            "share_count": 0,
            "parent_id": comment.get("parent_id"),
            "post_type": post_type,
            "search_term": search_term,
        }

    def collect_all(
        self,
        search_terms: list[str] | None = None,
        max_results_per_search: int = 25,
        max_comments_per_video: int = 100,
    ) -> list[dict]:
        """
        Full collection: search videos → fetch details → extract comments.
        Returns list of normalized post dicts.
        """
        terms = search_terms or YOUTUBE_SEARCH_TERMS
        seen_video_ids: set[str] = set()
        seen_comment_ids: set[str] = set()
        all_posts: list[dict] = []

        for term in terms:
            search_results = self.search_videos(term, max_results=max_results_per_search)

            # Extract video IDs from search results
            new_video_ids = []
            for item in search_results:
                vid = item.get("id", {})
                video_id = vid.get("videoId", "") if isinstance(vid, dict) else str(vid)
                if video_id and video_id not in seen_video_ids:
                    seen_video_ids.add(video_id)
                    new_video_ids.append(video_id)

            if not new_video_ids:
                continue

            # Fetch full video details (batch)
            details = self.get_video_details(new_video_ids)

            for video in details:
                normalized = self._normalize_video(video, search_term=term)
                all_posts.append(normalized)

                video_id = video.get("id", "")
                channel = video.get("snippet", {}).get("channelTitle", "unknown")
                video_url = f"https://www.youtube.com/watch?v={video_id}"

                # Fetch comments
                comments = self.get_video_comments(video_id, max_comments=max_comments_per_video)
                for comment in comments:
                    cid = comment["id"]
                    if cid not in seen_comment_ids:
                        seen_comment_ids.add(cid)
                        norm_comment = self._normalize_comment(
                            comment, video_url, channel, search_term=term
                        )
                        all_posts.append(norm_comment)

            # Check quota
            if self._quota_used > 9500:
                log.warning(f"Approaching daily quota limit ({self._quota_used}/10000). Stopping.")
                break

        log.info(
            f"YouTube collection complete: {len(seen_video_ids)} videos, "
            f"{len(seen_comment_ids)} comments, {self._quota_used} quota units used"
        )
        return all_posts


def collect_youtube_data(
    search_terms: list[str] | None = None,
    max_results_per_search: int = 25,
    max_comments_per_video: int = 100,
) -> list[dict]:
    """
    High-level function to collect YouTube data.
    Returns empty list if API key not configured.
    """
    api_key = os.environ.get("YOUTUBE_API_KEY")
    if not api_key:
        log.info("YOUTUBE_API_KEY not set — skipping YouTube collection")
        return []

    try:
        collector = YouTubeCollector(api_key=api_key)
        return collector.collect_all(
            search_terms=search_terms,
            max_results_per_search=max_results_per_search,
            max_comments_per_video=max_comments_per_video,
        )
    except ImportError as e:
        log.warning(f"YouTube collection skipped (missing dependency): {e}")
        return []
    except Exception as e:
        log.error(f"YouTube collection failed: {e}")
        return []


if __name__ == "__main__":
    import json

    posts = collect_youtube_data()
    print(f"Collected {len(posts)} YouTube posts")
    if posts:
        print(json.dumps(posts[0], indent=2, default=str))
