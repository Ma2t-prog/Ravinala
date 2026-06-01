"""
Ravinala — Market News Module
Real news from Yahoo Finance RSS + yfinance ticker news.
No API key required.
"""

from __future__ import annotations

import html
import re
import urllib.request
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from typing import List, Optional

import streamlit as st
import yfinance as yf


# ── Data model ─────────────────────────────────────────────────────────────

@dataclass
class Article:
    title: str
    url: str
    source: str
    published_at: datetime
    summary: str = ""
    thumbnail: Optional[str] = None
    sentiment: str = "neutral"
    sentiment_score: float = 0.0
    impact: str = "low"
    category: str = "other"


# ── Sentiment / impact helpers ─────────────────────────────────────────────

_BULLISH = {"rally": 0.8, "surge": 0.9, "beat": 0.7, "growth": 0.6, "rise": 0.6,
            "soar": 0.9, "jump": 0.8, "gains": 0.7, "strong": 0.7, "recovery": 0.7,
            "bull": 0.8, "bullish": 0.85, "boom": 0.8, "outperform": 0.8, "upgrade": 0.7}
_BEARISH = {"fall": -0.8, "crash": -0.9, "decline": -0.7, "drop": -0.7, "weak": -0.6,
            "loss": -0.7, "plunge": -0.9, "tumble": -0.8, "slump": -0.8, "bear": -0.8,
            "bearish": -0.85, "recession": -0.8, "crisis": -0.9, "miss": -0.7,
            "downgrade": -0.7, "selloff": -0.85}
_HIGH_IMPACT = {"earnings", "ipo", "merger", "acquisition", "fed", "ecb", "boe", "boj",
                "bankruptcy", "regulation", "lawsuit", "recall", "buyback", "gdp",
                "inflation", "nfp", "fomc", "rate", "dividend"}
_MEDIUM_IMPACT = {"analyst", "upgrade", "downgrade", "target", "split", "guidance"}


def _score_sentiment(text: str) -> tuple[str, float]:
    t = text.lower()
    score = sum(v for k, v in _BULLISH.items() if k in t) + \
            sum(v for k, v in _BEARISH.items() if k in t)
    score = max(-1.0, min(1.0, score))
    label = "bullish" if score > 0.2 else "bearish" if score < -0.2 else "neutral"
    return label, round(score, 3)


def _impact(text: str) -> str:
    t = text.lower()
    if any(k in t for k in _HIGH_IMPACT):
        return "high"
    if any(k in t for k in _MEDIUM_IMPACT):
        return "medium"
    return "low"


def _category(text: str) -> str:
    t = text.lower()
    if any(w in t for w in ("earnings", "ipo", "revenue", "profit")):
        return "earnings"
    if any(w in t for w in ("gdp", "inflation", "fed", "ecb", "rate", "nfp", "fomc", "macro")):
        return "economic"
    if any(w in t for w in ("merger", "acquisition", "takeover", "deal")):
        return "merger"
    if any(w in t for w in ("technical", "chart", "support", "resistance", "breakout")):
        return "technicals"
    return "other"


def _clean_html(text: str) -> str:
    text = re.sub(r"<[^>]+>", " ", text)
    return html.unescape(text).strip()


def _parse_rfc2822(s: str) -> datetime:
    try:
        return parsedate_to_datetime(s).astimezone(timezone.utc).replace(tzinfo=None)
    except Exception:
        return datetime.utcnow()


# ── Data fetchers ──────────────────────────────────────────────────────────

_RSS_FEEDS = {
    "Yahoo Finance — Top Stories":
        "https://feeds.finance.yahoo.com/rss/2.0/headline?s=^GSPC,^NDX,GC=F,CL=F&region=US&lang=en-US",
    "Yahoo Finance — Equities":
        "https://finance.yahoo.com/rss/topstories",
    "Yahoo Finance — Markets":
        "https://feeds.finance.yahoo.com/rss/2.0/headline?s=AAPL,MSFT,NVDA,AMZN,META,GOOGL&region=US&lang=en-US",
}

_UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"


def _fetch_rss(url: str, source: str, max_items: int = 15) -> List[Article]:
    articles: List[Article] = []
    try:
        req = urllib.request.Request(url, headers={"User-Agent": _UA})
        data = urllib.request.urlopen(req, timeout=8).read()
        root = ET.fromstring(data)
        for item in root.findall(".//item")[:max_items]:
            title   = _clean_html(item.findtext("title") or "")
            link    = (item.findtext("link") or "").strip()
            pub     = item.findtext("pubDate") or ""
            summary = _clean_html(item.findtext("description") or "")
            if not title or not link:
                continue
            sentiment, score = _score_sentiment(title + " " + summary)
            articles.append(Article(
                title=title,
                url=link,
                source=source,
                published_at=_parse_rfc2822(pub),
                summary=summary[:300] + ("…" if len(summary) > 300 else ""),
                sentiment=sentiment,
                sentiment_score=score,
                impact=_impact(title + " " + summary),
                category=_category(title + " " + summary),
            ))
    except Exception:
        pass
    return articles


def _fetch_yf_ticker_news(tickers: List[str], max_per_ticker: int = 5) -> List[Article]:
    articles: List[Article] = []
    seen: set[str] = set()
    for t in tickers:
        try:
            raw = yf.Ticker(t).news or []
            for item in raw[:max_per_ticker]:
                c = item.get("content", {})
                title = c.get("title", "")
                url   = (c.get("canonicalUrl") or c.get("clickThroughUrl") or {}).get("url", "")
                if not title or not url or url in seen:
                    continue
                seen.add(url)
                pub_str = c.get("pubDate", "")
                try:
                    pub = datetime.fromisoformat(pub_str.replace("Z", "+00:00")).replace(tzinfo=None)
                except Exception:
                    pub = datetime.utcnow()
                summary = _clean_html(c.get("summary") or c.get("description") or "")[:300]
                provider = (c.get("provider") or {}).get("displayName", "Yahoo Finance")
                thumb = None
                try:
                    resolutions = c.get("thumbnail", {}).get("resolutions", [])
                    if resolutions:
                        # pick 170px thumbnail if available
                        candidates = [r for r in resolutions if r.get("width", 0) <= 300]
                        thumb = (candidates[-1] if candidates else resolutions[0]).get("url")
                except Exception:
                    pass
                sentiment, score = _score_sentiment(title + " " + summary)
                articles.append(Article(
                    title=title,
                    url=url,
                    source=provider,
                    published_at=pub,
                    summary=summary + ("…" if len(summary) == 300 else ""),
                    thumbnail=thumb,
                    sentiment=sentiment,
                    sentiment_score=score,
                    impact=_impact(title + " " + summary),
                    category=_category(title + " " + summary),
                ))
        except Exception:
            continue
    return articles


@st.cache_data(ttl=300)
def fetch_all_news(ticker_query: str = "") -> List[Article]:
    """Fetch real news from RSS + yfinance. Cached 5 min."""
    articles: List[Article] = []
    seen_urls: set[str] = set()

    # 1. RSS feeds
    for source, url in _RSS_FEEDS.items():
        for a in _fetch_rss(url, source, max_items=20):
            if a.url not in seen_urls:
                seen_urls.add(a.url)
                articles.append(a)

    # 2. Ticker-specific news from yfinance
    base_tickers = ["^GSPC", "^NDX", "AAPL", "MSFT", "NVDA", "AMZN", "META", "GOOGL",
                    "GC=F", "CL=F", "EURUSD=X", "^VIX", "^TNX"]
    extra = [t.strip().upper() for t in ticker_query.split() if t.strip()] if ticker_query else []
    for a in _fetch_yf_ticker_news(extra + base_tickers[:6], max_per_ticker=6):
        if a.url not in seen_urls:
            seen_urls.add(a.url)
            articles.append(a)

    # Sort by recency
    articles.sort(key=lambda a: a.published_at, reverse=True)
    return articles


# ── Rendering helpers ──────────────────────────────────────────────────────

_SENT_COLOR  = {"bullish": "#10b981", "neutral": "#64748b", "bearish": "#ef4444"}
_SENT_LABEL  = {"bullish": "BULLISH", "neutral": "NEUTRAL", "bearish": "BEARISH"}
_IMP_COLOR   = {"high": "#f59e0b", "medium": "#60a5fa", "low": "#475569"}


def _time_ago(dt: datetime) -> str:
    mins = max(0, int((datetime.utcnow() - dt).total_seconds() / 60))
    if mins < 1:   return "Just now"
    if mins < 60:  return f"{mins}m ago"
    if mins < 1440: return f"{mins // 60}h ago"
    return f"{mins // 1440}d ago"


def _card(a: Article, compact: bool = False) -> None:
    sc  = _SENT_COLOR[a.sentiment]
    ic  = _IMP_COLOR[a.impact]
    sl  = _SENT_LABEL[a.sentiment]
    ago = _time_ago(a.published_at)

    if compact:
        st.markdown(
            f"<div style='padding:8px 0; border-bottom:1px solid #1e293b;'>"
            f"<a href='{a.url}' target='_blank' style='color:#e2e8f0;font-weight:600;"
            f"font-size:13px;text-decoration:none;line-height:1.4;'>{a.title}</a><br>"
            f"<span style='font-size:10px;color:{sc};font-weight:700;'>{sl}</span>"
            f"&nbsp;<span style='font-size:10px;color:{ic};'>●&nbsp;{a.impact.upper()}</span>"
            f"&nbsp;<span style='font-size:10px;color:#475569;'>{a.source} · {ago}</span>"
            f"</div>",
            unsafe_allow_html=True,
        )
        return

    # Detailed card
    cols = st.columns([5, 1]) if a.thumbnail else [st.container()]
    main = cols[0] if a.thumbnail else cols[0]

    with main:
        st.markdown(
            f"<a href='{a.url}' target='_blank' style='color:#f1f5f9;font-weight:700;"
            f"font-size:14px;text-decoration:none;line-height:1.4;display:block;margin-bottom:4px;'>"
            f"{a.title}</a>",
            unsafe_allow_html=True,
        )
        st.markdown(
            f"<div style='display:flex;gap:8px;align-items:center;flex-wrap:wrap;margin-bottom:6px;'>"
            f"<span style='background:{sc}22;color:{sc};font-size:9px;font-weight:800;"
            f"letter-spacing:.1em;padding:2px 7px;border-radius:3px;border:1px solid {sc}44;'>{sl}</span>"
            f"<span style='background:{ic}22;color:{ic};font-size:9px;font-weight:700;"
            f"padding:2px 7px;border-radius:3px;border:1px solid {ic}44;'>{a.impact.upper()}</span>"
            f"<span style='color:#64748b;font-size:11px;'>{a.source}</span>"
            f"<span style='color:#334155;font-size:11px;'>·</span>"
            f"<span style='color:#475569;font-size:11px;'>{ago}</span>"
            f"</div>",
            unsafe_allow_html=True,
        )
        if a.summary:
            st.markdown(
                f"<p style='color:#94a3b8;font-size:12px;line-height:1.5;margin:0 0 6px 0;'>"
                f"{a.summary}</p>",
                unsafe_allow_html=True,
            )
        st.markdown(
            f"<a href='{a.url}' target='_blank' style='font-size:11px;color:#00d9ff;"
            f"text-decoration:none;font-weight:600;'>Read full article →</a>",
            unsafe_allow_html=True,
        )

    if a.thumbnail and len(cols) > 1:
        with cols[1]:
            try:
                st.image(a.thumbnail, use_container_width=True)
            except Exception:
                pass

    st.markdown("<div style='height:1px;background:#1e293b;margin:10px 0;'></div>",
                unsafe_allow_html=True)


# ── Main UI ────────────────────────────────────────────────────────────────

def render_news_module() -> None:
    # Controls
    c1, c2, c3, c4, c5 = st.columns([2, 1.2, 1, 1, 0.8])
    with c1:
        ticker_q = st.text_input("Ticker / keyword search",
                                  placeholder="NVDA TSLA oil ECB…", key="news_ticker_q",
                                  label_visibility="collapsed")
    with c2:
        sort_by  = st.selectbox("Sort", ["Latest", "Impact", "Sentiment"],
                                 key="news_sort", label_visibility="collapsed")
    with c3:
        view_mode = st.selectbox("View", ["Detailed", "Compact"],
                                  key="news_view", label_visibility="collapsed")
    with c4:
        sent_filter = st.selectbox("Sentiment", ["All", "Bullish", "Neutral", "Bearish"],
                                    key="news_sent_filter", label_visibility="collapsed")
    with c5:
        refresh = st.button("Refresh", key="news_refresh")

    if refresh:
        st.cache_data.clear()

    with st.spinner("Fetching live news…"):
        articles = fetch_all_news(ticker_q)

    if not articles:
        st.warning("Could not fetch news — check internet connection.")
        return

    st.caption(f"**{len(articles)} articles** · Updated {datetime.utcnow().strftime('%H:%M UTC')}")
    st.divider()

    # Layout: feed | analytics
    feed_col, right_col = st.columns([2.8, 1], gap="small")

    # ── Analytics sidebar ────────────────────────────────────────────────
    with right_col:
        st.markdown("**Sentiment breakdown**")
        total = len(articles)
        for sent, col in _SENT_COLOR.items():
            n = sum(1 for a in articles if a.sentiment == sent)
            pct = n / total if total else 0
            st.markdown(
                f"<div style='display:flex;justify-content:space-between;font-size:11px;"
                f"color:#94a3b8;margin-bottom:2px;'><span style='color:{col};font-weight:700;'>"
                f"{sent.title()}</span><span>{n} ({pct*100:.0f}%)</span></div>",
                unsafe_allow_html=True,
            )
            st.progress(pct)

        st.markdown("<br>**Impact distribution**", unsafe_allow_html=True)
        for imp, col in _IMP_COLOR.items():
            n = sum(1 for a in articles if a.impact == imp)
            st.markdown(
                f"<div style='display:flex;justify-content:space-between;font-size:11px;"
                f"color:#94a3b8;margin-bottom:2px;'><span style='color:{col};font-weight:700;'>"
                f"{imp.title()}</span><span>{n}</span></div>",
                unsafe_allow_html=True,
            )

        st.markdown("<br>**Category breakdown**", unsafe_allow_html=True)
        cats = {}
        for a in articles:
            cats[a.category] = cats.get(a.category, 0) + 1
        for cat, n in sorted(cats.items(), key=lambda x: -x[1]):
            st.markdown(
                f"<div style='font-size:11px;color:#64748b;margin-bottom:2px;'>"
                f"{cat.title()}&nbsp;&nbsp;<b style='color:#94a3b8;'>{n}</b></div>",
                unsafe_allow_html=True,
            )

        st.markdown("<br>**Sources**", unsafe_allow_html=True)
        srcs = {}
        for a in articles:
            srcs[a.source] = srcs.get(a.source, 0) + 1
        for src, n in sorted(srcs.items(), key=lambda x: -x[1])[:8]:
            st.markdown(
                f"<div style='font-size:10px;color:#475569;margin-bottom:1px;'>"
                f"{src}&nbsp;<b style='color:#64748b;'>{n}</b></div>",
                unsafe_allow_html=True,
            )

    # ── News feed ────────────────────────────────────────────────────────
    with feed_col:
        # Filter
        filtered = articles
        if sent_filter != "All":
            filtered = [a for a in filtered if a.sentiment == sent_filter.lower()]
        if ticker_q.strip():
            q = ticker_q.lower()
            filtered = [a for a in filtered
                        if q in a.title.lower() or q in a.summary.lower()
                        or q in a.source.lower()]

        # Sort
        if sort_by == "Impact":
            _ord = {"high": 0, "medium": 1, "low": 2}
            filtered.sort(key=lambda a: _ord[a.impact])
        elif sort_by == "Sentiment":
            _ord2 = {"bullish": 0, "neutral": 1, "bearish": 2}
            filtered.sort(key=lambda a: _ord2[a.sentiment])

        if not filtered:
            st.info("No articles match your filters.")
        else:
            compact = view_mode == "Compact"
            for a in filtered:
                _card(a, compact=compact)
