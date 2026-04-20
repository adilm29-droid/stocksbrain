"""
news.py — Fetches and analyses Yahoo Finance RSS news headlines for thesis-break signals.

Functions:
    get_news_sentiment(ticker) -> dict
"""

import sys

try:
    import feedparser
except ImportError:
    feedparser = None

YAHOO_RSS_URL = "https://feeds.finance.yahoo.com/rss/2.0/headline?s={ticker}&region=US&lang=en-US"

THESIS_BREAK_KEYWORDS = [
    "guidance cut",
    "lowered guidance",
    "cuts guidance",
    "missed estimates",
    "earnings miss",
    "ceo resign",
    "ceo depart",
    "ceo steps down",
    "ceo fired",
    "sec probe",
    "sec investigation",
    "regulatory",
    "fda reject",
    "recall",
    "bankruptcy",
    "chapter 11",
    "downgrade",
    "product failure",
    "data breach",
    "class action",
    "antitrust",
    "fraud",
]

POSITIVE_KEYWORDS = [
    "beat estimates",
    "earnings beat",
    "record revenue",
    "raised guidance",
    "upgrades",
    "strong quarter",
    "blowout",
    "buyback",
    "dividend increase",
    "partnership",
    "acquisition",
    "new contract",
    "fda approval",
]

NEGATIVE_KEYWORDS = [
    "miss",
    "loss",
    "decline",
    "plunge",
    "crash",
    "lawsuit",
    "probe",
    "cut",
    "resign",
    "layoff",
    "warning",
    "recall",
    "fail",
    "downgrade",
    "investigation",
]


def _score_headline(text: str) -> float:
    """Returns +1, -1, or 0 based on keyword presence in headline."""
    lower = text.lower()
    pos = sum(1 for kw in POSITIVE_KEYWORDS if kw in lower)
    neg = sum(1 for kw in NEGATIVE_KEYWORDS if kw in lower)
    raw = pos - neg
    if raw > 0:
        return 1.0
    elif raw < 0:
        return -1.0
    return 0.0


def get_news_sentiment(ticker: str) -> dict:
    """
    Fetch latest Yahoo Finance headlines via RSS and compute sentiment.

    Returns dict:
        sentiment_score (float, -1 to 1)
        headline_count (int)
        top_headlines (list of str)
        thesis_break_flags (list of str) — specific concerning phrases found
    """
    if feedparser is None:
        return {
            "sentiment_score": 0.0,
            "headline_count": 0,
            "top_headlines": [],
            "thesis_break_flags": [],
            "error": "feedparser not installed",
        }

    url = YAHOO_RSS_URL.format(ticker=ticker)
    try:
        feed = feedparser.parse(url)
        entries = feed.get("entries", [])
    except Exception as exc:
        print(f"[ERROR] news.get_news_sentiment({ticker}): {exc}", file=sys.stderr)
        return {
            "sentiment_score": 0.0,
            "headline_count": 0,
            "top_headlines": [],
            "thesis_break_flags": [],
            "error": str(exc),
        }

    if not entries:
        return {
            "sentiment_score": 0.0,
            "headline_count": 0,
            "top_headlines": [],
            "thesis_break_flags": [],
        }

    headlines = []
    for entry in entries[:20]:
        title = entry.get("title", "")
        summary = entry.get("summary", "")
        combined = f"{title} {summary}".strip()
        if combined:
            headlines.append(combined)

    # Compute sentiment
    scores = [_score_headline(h) for h in headlines]
    avg_score = round(sum(scores) / len(scores), 3) if scores else 0.0

    # Detect thesis-break flags
    thesis_flags = []
    for headline in headlines:
        lower = headline.lower()
        for kw in THESIS_BREAK_KEYWORDS:
            if kw in lower and kw not in thesis_flags:
                thesis_flags.append(kw)

    top_headlines = [h[:120] for h in headlines[:5]]  # top 5, truncated

    return {
        "sentiment_score": avg_score,
        "headline_count": len(headlines),
        "top_headlines": top_headlines,
        "thesis_break_flags": thesis_flags,
    }
