"""
News Comment Collector — Scrapes public comment sections from Chicago news sites.

Targets: Block Club Chicago, WBEZ, Chicago Sun-Times, South Side Weekly, AP News.
Approach: BeautifulSoup + requests with respectful rate limiting and robots.txt compliance.
"""

import hashlib
import re
import time
from datetime import datetime, timezone
from typing import Generator
from urllib.parse import quote_plus, urljoin

import requests
from bs4 import BeautifulSoup

from src.utils.logger import log


class RateLimiter:
    def __init__(self, min_delay: float = 3.0):
        self.min_delay = min_delay
        self._last = 0.0

    def wait(self):
        elapsed = time.time() - self._last
        if elapsed < self.min_delay:
            time.sleep(self.min_delay - elapsed)
        self._last = time.time()


# ── News Source Definitions ──────────────────────────────
NEWS_SOURCES = [
    {
        "name": "Block Club Chicago",
        "domain": "blockclubchicago.org",
        "search_url": "https://blockclubchicago.org/?s={query}",
        "article_selector": "h3.entry-title a, h2.entry-title a, .post-title a",
        "comment_selector": ".comment-content p, .comment-body p, .disqus-comment p",
        "date_selector": "time.entry-date, .post-date, time[datetime]",
        "rate_limit": 3.0,
    },
    {
        "name": "WBEZ",
        "domain": "wbez.org",
        "search_url": "https://www.wbez.org/search#term={query}",
        "article_selector": "h3 a, .search-result a, .story-card a",
        "comment_selector": ".comment-text p, .comment-body p",
        "date_selector": "time[datetime], .date, .published-date",
        "rate_limit": 3.0,
    },
    {
        "name": "Chicago Sun-Times",
        "domain": "chicago.suntimes.com",
        "search_url": "https://chicago.suntimes.com/?s={query}",
        "article_selector": "h3 a, .story-title a, .entry-title a",
        "comment_selector": ".comment-content p, .comment-text p",
        "date_selector": "time[datetime], .entry-date",
        "rate_limit": 3.0,
    },
    {
        "name": "South Side Weekly",
        "domain": "southsideweekly.com",
        "search_url": "https://southsideweekly.com/?s={query}",
        "article_selector": "h2.entry-title a, h3 a, .post-title a",
        "comment_selector": ".comment-content p, .comment-body p",
        "date_selector": "time[datetime], .entry-date",
        "rate_limit": 3.0,
    },
    {
        "name": "AP News",
        "domain": "apnews.com",
        "search_url": "https://apnews.com/search?q={query}",
        "article_selector": ".PagePromo-title a, .SearchResultsModule-title a, h2 a",
        "comment_selector": ".comment-content p",
        "date_selector": "time[datetime], .Timestamp",
        "rate_limit": 3.0,
    },
]

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36 "
        "SouthShoreSentimentStudy/1.0"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
}


class NewsCollector:
    """Collect comments from news article pages."""

    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update(HEADERS)
        self.limiter = RateLimiter(3.0)

    def _check_robots(self, domain: str) -> bool:
        """Basic robots.txt check."""
        try:
            resp = self.session.get(f"https://{domain}/robots.txt", timeout=10)
            if resp.status_code == 200:
                text = resp.text.lower()
                # Very basic check — if User-agent: * has Disallow: / we skip
                if "disallow: /" in text and "allow:" not in text:
                    log.warning(f"robots.txt blocks scraping for {domain}")
                    return False
            return True
        except Exception:
            return True  # If we can't check, proceed cautiously

    def _find_article_urls(self, source: dict, query: str) -> list[str]:
        """Search a news site and extract article URLs."""
        self.limiter.wait()

        search_url = source["search_url"].format(query=quote_plus(query))
        urls = []

        try:
            resp = self.session.get(search_url, timeout=15)
            resp.raise_for_status()
            soup = BeautifulSoup(resp.text, "lxml")

            for selector in source["article_selector"].split(", "):
                for link in soup.select(selector):
                    href = link.get("href")
                    if href:
                        full_url = urljoin(f"https://{source['domain']}", href)
                        if source["domain"] in full_url:
                            urls.append(full_url)

            urls = list(dict.fromkeys(urls))[:10]  # Dedupe, max 10 articles
            log.info(f"Found {len(urls)} article URLs on {source['name']} for '{query}'")
        except requests.RequestException as e:
            log.warning(f"Search failed for {source['name']}: {e}")

        return urls

    def _extract_article_metadata(self, soup: BeautifulSoup, source: dict, url: str) -> dict:
        """Extract article title, date, and text."""
        # Title
        title_tag = soup.find("h1") or soup.find("title")
        title = title_tag.get_text(strip=True) if title_tag else ""

        # Date
        date_str = None
        for selector in source["date_selector"].split(", "):
            date_el = soup.select_one(selector)
            if date_el:
                date_str = date_el.get("datetime") or date_el.get_text(strip=True)
                break

        dt = None
        if date_str:
            for fmt in [
                "%Y-%m-%dT%H:%M:%S%z",
                "%Y-%m-%dT%H:%M:%S.%f%z",
                "%Y-%m-%d",
                "%B %d, %Y",
                "%b %d, %Y",
            ]:
                try:
                    dt = datetime.strptime(date_str.strip()[:25], fmt)
                    if dt.tzinfo is None:
                        dt = dt.replace(tzinfo=timezone.utc)
                    break
                except ValueError:
                    continue
        if dt is None:
            dt = datetime.now(timezone.utc)

        # Article body text (for context, not published verbatim)
        article_text = ""
        for tag in soup.find_all(
            ["article", "div"], class_=re.compile(r"entry-content|article-body|story-body")
        ):
            article_text = " ".join(p.get_text(strip=True) for p in tag.find_all("p"))
            if article_text:
                break

        return {"title": title, "dt": dt, "article_text": article_text[:500]}

    def _extract_comments(self, soup: BeautifulSoup, source: dict) -> list[dict]:
        """Extract comment text from article page."""
        comments = []

        for selector in source["comment_selector"].split(", "):
            for el in soup.select(selector):
                text = el.get_text(strip=True)
                if text and len(text) > 10:
                    comments.append(
                        {
                            "text": text,
                            "author": "anonymous",
                        }
                    )

        # Also try common Disqus / comment-list patterns
        for comment_block in soup.select(".comment, .dsq-comment, [data-comment-id]"):
            body = comment_block.select_one(".comment-body, .comment-content, .post-body")
            author_el = comment_block.select_one(".author, .username, .comment-author")
            if body:
                text = body.get_text(strip=True)
                author = author_el.get_text(strip=True) if author_el else "anonymous"
                if text and len(text) > 10:
                    comments.append({"text": text, "author": author})

        # Deduplicate by text
        seen = set()
        unique = []
        for c in comments:
            if c["text"] not in seen:
                seen.add(c["text"])
                unique.append(c)

        return unique

    def collect_from_source(
        self, source: dict, queries: list[str] | None = None
    ) -> Generator[dict, None, None]:
        """Collect comments from a single news source."""
        if not self._check_robots(source["domain"]):
            log.warning(f"Skipping {source['name']} due to robots.txt")
            return

        terms = queries or [
            "South Shore ICE raid",
            "Chicago ICE raid apartment",
            "Operation Midway Blitz",
        ]

        seen_urls = set()
        post_count = 0

        for term in terms:
            article_urls = self._find_article_urls(source, term)

            for url in article_urls:
                if url in seen_urls:
                    continue
                seen_urls.add(url)

                self.limiter.wait()
                try:
                    resp = self.session.get(url, timeout=15)
                    resp.raise_for_status()
                    soup = BeautifulSoup(resp.text, "lxml")

                    metadata = self._extract_article_metadata(soup, source, url)
                    comments = self._extract_comments(soup, source)

                    # Yield the article itself as a post
                    article_id = hashlib.md5(url.encode()).hexdigest()[:12]
                    yield {
                        "id": f"news_art_{article_id}",
                        "platform": "news_comment",
                        "source": source["name"],
                        "url": url,
                        "dt_utc": metadata["dt"].isoformat(),
                        "text": f"{metadata['title']}. {metadata['article_text']}",
                        "title": metadata["title"],
                        "author_display": source["name"],
                        "score": 0,
                        "like_count": 0,
                        "reply_count": len(comments),
                        "share_count": 0,
                        "parent_id": None,
                        "post_type": "article",
                        "search_term": term,
                    }
                    post_count += 1

                    # Yield comments
                    for i, comment in enumerate(comments):
                        comment_id = hashlib.md5(
                            f"{url}_{i}_{comment['text'][:50]}".encode()
                        ).hexdigest()[:12]
                        yield {
                            "id": f"news_com_{comment_id}",
                            "platform": "news_comment",
                            "source": source["name"],
                            "url": url,
                            "dt_utc": metadata["dt"].isoformat(),
                            "text": comment["text"],
                            "title": None,
                            "author_display": comment["author"],
                            "score": 0,
                            "like_count": 0,
                            "reply_count": 0,
                            "share_count": 0,
                            "parent_id": f"news_art_{article_id}",
                            "post_type": "comment",
                            "search_term": term,
                        }
                        post_count += 1

                except requests.RequestException as e:
                    log.warning(f"Failed to fetch {url}: {e}")

        log.info(f"Collected {post_count} items from {source['name']}")

    def collect_all(self, queries: list[str] | None = None) -> list[dict]:
        """Collect from all configured news sources."""
        results = []
        seen_ids = set()

        for source in NEWS_SOURCES:
            for post in self.collect_from_source(source, queries):
                if post["id"] not in seen_ids:
                    seen_ids.add(post["id"])
                    results.append(post)

        log.info(f"Total news items collected: {len(results)}")
        return results


if __name__ == "__main__":
    import json

    collector = NewsCollector()
    posts = collector.collect_all()
    print(f"Collected {len(posts)} news items")
    if posts:
        print(json.dumps(posts[0], indent=2, default=str))
