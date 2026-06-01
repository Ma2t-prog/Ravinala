"""Ravinala — Equity Research Module
One-click research report: profile, valuation comps, relative performance,
news sentiment & investment pitch (thesis / risks / target price).
PDF export via reportlab.
"""

import io
import warnings
from datetime import datetime
from typing import Dict, List, Optional, Tuple

import numpy as np
import pandas as pd
import yfinance as yf

warnings.filterwarnings("ignore")


# ─────────────────────────────────────────────────────────────────────────────
# 1. PEER GROUPS  (GICS-aligned)
# ─────────────────────────────────────────────────────────────────────────────

SECTOR_PEERS: Dict[str, List[str]] = {
    "Technology": ["AAPL", "MSFT", "GOOGL", "META", "NVDA", "TSM", "AVGO", "ORCL", "AMD", "INTC"],
    "Consumer Cyclical": ["AMZN", "TSLA", "HD", "NKE", "MCD", "SBUX", "LOW", "TGT", "BKNG", "ABNB"],
    "Consumer Defensive": ["WMT", "KO", "PEP", "PG", "COST", "PM", "MO", "CL", "GIS", "EL"],
    "Healthcare": ["JNJ", "UNH", "MRK", "LLY", "ABBV", "PFE", "TMO", "DHR", "AMGN", "BMY"],
    "Financial Services": ["JPM", "V", "MA", "BAC", "WFC", "GS", "MS", "AXP", "BLK", "C"],
    "Energy": ["XOM", "CVX", "COP", "SLB", "EOG", "MPC", "PSX", "VLO", "OXY", "BP"],
    "Industrials": ["RTX", "HON", "GE", "CAT", "DE", "UPS", "LMT", "BA", "NOC", "EMR"],
    "Communication Services": ["GOOGL", "META", "NFLX", "DIS", "CMCSA", "T", "VZ", "TMUS", "SNAP", "PINS"],
    "Real Estate": ["AMT", "PLD", "CCI", "EQIX", "PSA", "O", "DLR", "WELL", "SPG", "AVB"],
    "Utilities": ["NEE", "DUK", "SO", "D", "AEP", "SRE", "XEL", "ED", "EIX", "WEC"],
    "Basic Materials": ["LIN", "APD", "SHW", "ECL", "NEM", "FCX", "NUE", "VMC", "MLM", "ALB"],
}

# ─────────────────────────────────────────────────────────────────────────────
# 2. TOP 20 MOST-RESEARCHED EQUITIES
# ─────────────────────────────────────────────────────────────────────────────

TOP_20_EQUITIES = pd.DataFrame({
    "Ticker": ["AAPL", "MSFT", "NVDA", "GOOGL", "META", "TSLA", "AMZN", "JPM", "V", "MA",
               "NFLX", "JNJ", "XOM", "WMT", "CVX", "UNH", "BAC", "GS", "INTC", "AMD"],
    "Company": [
        "Apple Inc.", "Microsoft Corp", "NVIDIA Corp", "Alphabet Inc.", "Meta Platforms",
        "Tesla Inc.", "Amazon.com Inc.", "JPMorgan Chase", "Visa Inc.", "Mastercard Inc.",
        "Netflix Inc.", "Johnson & Johnson", "Exxon Mobil", "Walmart Inc.", "Chevron Corp",
        "UnitedHealth Group", "Bank of America", "Goldman Sachs", "Intel Corp", "Advanced Micro Devices"
    ],
    "Sector": [
        "Technology", "Technology", "Technology", "Communication Services", "Communication Services",
        "Consumer Cyclical", "Consumer Cyclical", "Financial Services", "Financial Services", "Financial Services",
        "Communication Services", "Healthcare", "Energy", "Consumer Defensive", "Energy",
        "Healthcare", "Financial Services", "Financial Services", "Technology", "Technology"
    ],
    "P/E": [32.5, 36.2, 68.4, 26.3, 42.1, 78.3, 52.1, 14.2, 48.6, 44.3, 68.9, 18.4, 12.1, 28.3, 11.8, 25.6, 13.1, 15.2, 19.4, 142.5],
    "Market Cap ($T)": [3.4, 3.1, 1.8, 1.6, 1.2, 1.1, 2.0, 0.54, 0.78, 0.68, 0.25, 0.40, 0.50, 0.42, 0.27, 0.58, 0.35, 0.14, 0.19, 0.25],
    "Coverage": ["Very High", "Very High", "Very High", "Very High", "Very High", "Very High", "Very High", "Very High", "High", "High",
                 "High", "Very High", "High", "High", "High", "High", "Very High", "High", "Very High", "High"],
})

# ─────────────────────────────────────────────────────────────────────────────
# 3. BENCHMARK SELECTOR
# ─────────────────────────────────────────────────────────────────────────────

def _get_benchmark(ticker: str) -> Tuple[str, str]:
    """Return (benchmark_ticker, label) based on exchange suffix."""
    t = ticker.upper()
    if any(t.endswith(sfx) for sfx in (".PA", ".F", ".AS", ".MI", ".MC", ".BR", ".VI")):
        return "^STOXX50E", "Euro Stoxx 50"
    if t.endswith(".L"):
        return "^FTSE", "FTSE 100"
    if t.endswith(".T"):
        return "^N225", "Nikkei 225"
    if t.endswith(".HK"):
        return "^HSI", "Hang Seng"
    if t.endswith(".TO") or t.endswith(".V"):
        return "^GSPTSE", "TSX Composite"
    return "^GSPC", "S&P 500"


# ─────────────────────────────────────────────────────────────────────────────
# 3. SENTIMENT KEYWORDS
# ─────────────────────────────────────────────────────────────────────────────

_BULLISH = {
    "beat", "beats", "surge", "surges", "strong", "growth", "record", "upgrade",
    "outperform", "raises", "profit", "positive", "buyback", "dividend", "exceeds",
    "breakthrough", "partnership", "acquisition", "momentum", "rally", "wins",
    "deal", "contract", "buy", "approve", "approved", "expands", "expansion",
    "raised", "hikes", "raises", "solid", "better", "ahead",
}
_BEARISH = {
    "miss", "misses", "weak", "decline", "cut", "cuts", "downgrade", "underperform",
    "loss", "fall", "falls", "disappoint", "disappoints", "recall", "lawsuit", "fine",
    "investigation", "layoff", "layoffs", "warning", "lowered", "concern", "risk",
    "sell", "below", "drops", "drop", "probe", "delay", "delays", "suspended",
    "bankruptcy", "default", "charge", "charges", "slump",
}


# ─────────────────────────────────────────────────────────────────────────────
# 4. EQUITY RESEARCH ENGINE
# ─────────────────────────────────────────────────────────────────────────────

class EquityResearchEngine:
    """Fetch and compute all data required for the equity research report."""

    def __init__(self, ticker: str):
        self.ticker = ticker.upper().strip()
        self._yft = yf.Ticker(self.ticker)
        self._info: Optional[Dict] = None

    # ── Helpers ───────────────────────────────────────────────────────────────

    def _info_safe(self) -> Dict:
        if self._info is None:
            try:
                self._info = self._yft.info or {}
            except Exception:
                self._info = {}
        return self._info

    @staticmethod
    def _fmt_large(val) -> str:
        try:
            v = float(val)
        except (TypeError, ValueError):
            return "N/A"
        if v >= 1e12:
            return f"${v/1e12:.2f}T"
        if v >= 1e9:
            return f"${v/1e9:.2f}B"
        if v >= 1e6:
            return f"${v/1e6:.2f}M"
        return f"${v:,.0f}"

    # ── Company Profile ───────────────────────────────────────────────────────

    def get_profile(self) -> Dict:
        info = self._info_safe()
        return {
            "name":        info.get("longName") or info.get("shortName") or self.ticker,
            "sector":      info.get("sector", "N/A"),
            "industry":    info.get("industry", "N/A"),
            "country":     info.get("country", "N/A"),
            "exchange":    info.get("exchange", "N/A"),
            "currency":    info.get("currency", "USD"),
            "description": (info.get("longBusinessSummary") or "")[:450],
            "website":     info.get("website", ""),
            "employees":   info.get("fullTimeEmployees"),
        }

    # ── Key Metrics ───────────────────────────────────────────────────────────

    def get_key_metrics(self) -> Dict:
        info  = self._info_safe()
        price = info.get("currentPrice") or info.get("regularMarketPrice")
        prev  = info.get("previousClose") or info.get("regularMarketPreviousClose")
        chg   = ((price - prev) / prev * 100) if (price and prev and prev != 0) else None
        return {
            "price":           price,
            "change_pct":      chg,
            "market_cap":      info.get("marketCap"),
            "market_cap_fmt":  self._fmt_large(info.get("marketCap")),
            "pe_trailing":     info.get("trailingPE"),
            "pe_forward":      info.get("forwardPE"),
            "eps_trailing":    info.get("trailingEps"),
            "eps_forward":     info.get("forwardEps"),
            "div_yield":       info.get("dividendYield"),
            "beta":            info.get("beta"),
            "52w_high":        info.get("fiftyTwoWeekHigh"),
            "52w_low":         info.get("fiftyTwoWeekLow"),
            "avg_volume":      info.get("averageVolume"),
            "ev":              info.get("enterpriseValue"),
            "ev_ebitda":       info.get("enterpriseToEbitda"),
            "ev_revenue":      info.get("enterpriseToRevenue"),
            "price_to_book":   info.get("priceToBook"),
            "price_to_sales":  info.get("priceToSalesTrailing12Months"),
            "roe":             info.get("returnOnEquity"),
            "roa":             info.get("returnOnAssets"),
            "profit_margin":   info.get("profitMargins"),
            "revenue_growth":  info.get("revenueGrowth"),
            "earnings_growth": info.get("earningsGrowth"),
        }

    # ── Price History ─────────────────────────────────────────────────────────

    def get_price_history(self, period: str = "1y") -> Optional[pd.DataFrame]:
        try:
            hist = self._yft.history(period=period)
            return hist[["Close"]].copy() if not hist.empty else None
        except Exception:
            return None

    def get_benchmark_history(self, period: str = "1y") -> Tuple[Optional[pd.DataFrame], str, str]:
        bmk_ticker, bmk_label = _get_benchmark(self.ticker)
        try:
            hist = yf.Ticker(bmk_ticker).history(period=period)
            return (hist[["Close"]].copy() if not hist.empty else None), bmk_ticker, bmk_label
        except Exception:
            return None, bmk_ticker, bmk_label

    # ── Financial Statements ──────────────────────────────────────────────────

    def get_financials(self) -> Dict:
        """Revenue, Net Income, Gross Profit for last 4 fiscal years."""
        result: Dict = {"years": [], "revenue": [], "net_income": [], "gross_profit": []}
        try:
            stmt = self._yft.income_stmt
            if stmt is None or stmt.empty:
                return result

            rev_row  = None
            ni_row   = None
            gp_row   = None
            for idx in stmt.index:
                s = str(idx).lower()
                if "total revenue" in s:
                    rev_row = stmt.loc[idx]
                if "net income" in s and "minority" not in s and "noncontrolling" not in s:
                    ni_row = stmt.loc[idx]
                if "gross profit" in s:
                    gp_row = stmt.loc[idx]

            if rev_row is None:
                return result

            cols = list(stmt.columns)[:4]
            for col in cols:
                y = str(col.year) if hasattr(col, "year") else str(col)[:4]
                result["years"].append(y)
                result["revenue"].append(float(rev_row[col]) if pd.notna(rev_row[col]) else 0)
                result["net_income"].append(float(ni_row[col]) if (ni_row is not None and pd.notna(ni_row[col])) else 0)
                result["gross_profit"].append(float(gp_row[col]) if (gp_row is not None and pd.notna(gp_row[col])) else 0)

            # Oldest → newest
            for k in result:
                result[k] = list(reversed(result[k]))

        except Exception:
            pass
        return result

    # ── Peer Multiples ────────────────────────────────────────────────────────

    def get_peers(self, n: int = 5) -> List[str]:
        sector = self._info_safe().get("sector", "")
        pool   = SECTOR_PEERS.get(sector, SECTOR_PEERS["Technology"])
        return [p for p in pool if p.upper() != self.ticker][:n]

    def get_peer_multiples(self) -> pd.DataFrame:
        peers      = self.get_peers(5)
        all_tickers = [self.ticker] + peers
        rows = []
        for t in all_tickers:
            try:
                info = yf.Ticker(t).info
                rows.append({
                    "Ticker":        t,
                    "P/E (TTM)":     info.get("trailingPE"),
                    "P/E (Fwd)":     info.get("forwardPE"),
                    "EV/EBITDA":     info.get("enterpriseToEbitda"),
                    "P/S":           info.get("priceToSalesTrailing12Months"),
                    "P/B":           info.get("priceToBook"),
                    "Div Yield (%)": round(float(info.get("dividendYield") or 0) * 100, 2),
                    "Mkt Cap":       self._fmt_large(info.get("marketCap")),
                })
            except Exception:
                rows.append({"Ticker": t})

        df = pd.DataFrame(rows).set_index("Ticker")
        for col in ["P/E (TTM)", "P/E (Fwd)", "EV/EBITDA", "P/S", "P/B"]:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors="coerce").round(1)
        return df

    # ── News & Sentiment ──────────────────────────────────────────────────────

    def get_news(self, n: int = 5) -> List[Dict]:
        try:
            return (self._yft.news or [])[:n]
        except Exception:
            return []

    def score_sentiment(self, news: List[Dict]) -> Dict:
        bull, bear = 0, 0
        for item in news:
            words = set(item.get("title", "").lower().split())
            bull += len(words & _BULLISH)
            bear += len(words & _BEARISH)
        total = bull + bear
        if total == 0:
            return {"label": "Neutral", "score": 50, "bull": 0, "bear": 0}
        if bull > bear:
            return {"label": "Bullish", "score": min(100, int(50 + bull / total * 50)), "bull": bull, "bear": bear}
        if bear > bull:
            return {"label": "Bearish", "score": max(0, int(50 - bear / total * 50)), "bull": bull, "bear": bear}
        return {"label": "Neutral", "score": 50, "bull": bull, "bear": bear}

    # ── Analyst Targets ───────────────────────────────────────────────────────

    def get_analyst_targets(self) -> Dict:
        info = self._info_safe()
        return {
            "target_mean":    info.get("targetMeanPrice"),
            "target_high":    info.get("targetHighPrice"),
            "target_low":     info.get("targetMedianPrice"),
            "recommendation": (info.get("recommendationKey") or "N/A").upper().replace("_", " "),
            "nb_analysts":    info.get("numberOfAnalystOpinions"),
        }

    # ── Investment Pitch ──────────────────────────────────────────────────────

    def generate_investment_pitch(self) -> Dict:
        profile  = self.get_profile()
        metrics  = self.get_key_metrics()
        analyst  = self.get_analyst_targets()

        # Target price: analyst consensus, fallback to sector P/E × fwd EPS
        target_price  = analyst.get("target_mean")
        target_method = "Analyst Consensus (Mean)"
        if not target_price and metrics.get("eps_forward"):
            _sector_pe = {
                "Technology": 28, "Consumer Cyclical": 22, "Healthcare": 20,
                "Financial Services": 15, "Energy": 14, "Industrials": 18,
                "Communication Services": 24, "Consumer Defensive": 20,
                "Basic Materials": 16, "Real Estate": 22, "Utilities": 18,
            }
            ref_pe = _sector_pe.get(profile.get("sector", ""), 20)
            try:
                target_price  = float(metrics["eps_forward"]) * ref_pe
                target_method = f"Forward EPS × Sector P/E ({ref_pe}×)"
            except (TypeError, ValueError):
                pass

        current = metrics.get("price") or 0
        upside  = ((target_price - current) / current * 100) if (target_price and current > 0) else None

        # Thesis bullets
        thesis = []
        if metrics.get("revenue_growth") and metrics["revenue_growth"] > 0.08:
            thesis.append(f"Revenue growing at {metrics['revenue_growth']*100:.1f}% YoY — healthy demand expansion.")
        if metrics.get("profit_margin") and metrics["profit_margin"] > 0.15:
            thesis.append(f"Net margin of {metrics['profit_margin']*100:.1f}% reflects strong pricing power.")
        rec = analyst.get("recommendation", "")
        if "BUY" in rec or "STRONG" in rec:
            nb = analyst.get("nb_analysts", "N/A")
            thesis.append(f"Analyst consensus: {rec} ({nb} analysts).")
        if upside and upside > 10:
            thesis.append(f"Analyst targets imply {upside:.1f}% upside from current levels.")
        pe_t = metrics.get("pe_trailing")
        pe_f = metrics.get("pe_forward")
        if pe_t and pe_f and pe_f < pe_t:
            thesis.append("Forward P/E below trailing — earnings acceleration expected.")
        if not thesis:
            thesis = [
                f"{profile.get('name', self.ticker)} operates in {profile.get('sector','N/A')} with growth potential.",
                "Monitor earnings cadence and macro environment for near-term catalysts.",
            ]

        # Risk bullets
        risks = []
        beta = metrics.get("beta")
        if beta and beta > 1.3:
            risks.append(f"High beta ({beta:.2f}) — stock amplifies broad market moves.")
        if pe_t and pe_t > 35:
            risks.append(f"Elevated P/E ({pe_t:.0f}×) — limited margin of safety if growth disappoints.")
        eg = metrics.get("earnings_growth")
        if eg is not None and eg < 0:
            risks.append("Negative earnings growth — profitability may be under pressure.")
        dy = metrics.get("div_yield")
        if not dy or dy < 0.005:
            risks.append("No significant dividend — return purely reliant on capital appreciation.")
        risks.append("Macro headwinds: rate changes, FX volatility, and geopolitical uncertainty.")
        if len(risks) < 3:
            risks.insert(0, "Sector rotation risk if investors shift to defensive / value assets.")

        return {
            "thesis_bullets": thesis,
            "risk_bullets":   risks,
            "target_price":   target_price,
            "target_method":  target_method,
            "upside":         upside,
            "recommendation": rec,
        }

    # ── Full Fetch ────────────────────────────────────────────────────────────

    def fetch_all(self) -> Dict:
        try:
            info = self._info_safe()
            if not info or (not info.get("regularMarketPrice") and not info.get("currentPrice")):
                return {"error": f"No market data found for '{self.ticker}'. Verify the symbol."}
            return {
                "error":   None,
                "profile": self.get_profile(),
                "metrics": self.get_key_metrics(),
                "analyst": self.get_analyst_targets(),
                "news":    self.get_news(5),
            }
        except Exception as e:
            return {"error": f"Failed to fetch '{self.ticker}': {e}"}


# ─────────────────────────────────────────────────────────────────────────────
# 5. PDF REPORT GENERATOR
# ─────────────────────────────────────────────────────────────────────────────

def generate_equity_report_pdf(
    ticker: str,
    profile: Dict,
    metrics: Dict,
    analyst: Dict,
    pitch: Dict,
    news: List[Dict],
    sentiment: Dict,
) -> Optional[bytes]:
    """Build a professional A4 equity research report PDF via reportlab."""
    try:
        from reportlab.lib import colors
        from reportlab.lib.enums import TA_CENTER, TA_LEFT
        from reportlab.lib.pagesizes import A4
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.lib.units import cm
        from reportlab.platypus import (
            HRFlowable, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle,
        )

        buf = io.BytesIO()
        doc = SimpleDocTemplate(
            buf, pagesize=A4,
            leftMargin=1.8*cm, rightMargin=1.8*cm,
            topMargin=1.8*cm,  bottomMargin=1.8*cm,
        )
        styles = getSampleStyleSheet()

        S_TITLE   = ParagraphStyle("RTitle",   parent=styles["Title"],
                                   fontSize=20, textColor=colors.HexColor("#6366f1"), spaceAfter=2)
        S_H1      = ParagraphStyle("RH1",      parent=styles["Heading1"],
                                   fontSize=14, textColor=colors.HexColor("#1e1b4b"), spaceAfter=4)
        S_H2      = ParagraphStyle("RH2",      parent=styles["Heading2"],
                                   fontSize=11, textColor=colors.HexColor("#4338ca"),
                                   spaceBefore=12, spaceAfter=4)
        S_BODY    = ParagraphStyle("RBody",    parent=styles["Normal"],
                                   fontSize=9,  textColor=colors.HexColor("#374151"),
                                   spaceAfter=3, leading=13)
        S_CAPTION = ParagraphStyle("RCaption", parent=styles["Normal"],
                                   fontSize=7.5, textColor=colors.HexColor("#6b7280"), spaceAfter=2)
        S_BULLET  = ParagraphStyle("RBullet",  parent=styles["Normal"],
                                   fontSize=9,  textColor=colors.HexColor("#374151"),
                                   spaceAfter=3, leading=13, leftIndent=12)

        _INDIGO   = colors.HexColor("#6366f1")
        _SLATE    = colors.HexColor("#e5e7eb")
        _ROW_A    = colors.HexColor("#f5f3ff")
        _ROW_B    = colors.white
        _TBL_HDR  = colors.HexColor("#4338ca")

        def _tbl_style(header_color=_TBL_HDR):
            return TableStyle([
                ("BACKGROUND",    (0, 0), (-1, 0), header_color),
                ("TEXTCOLOR",     (0, 0), (-1, 0), colors.white),
                ("FONTNAME",      (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTSIZE",      (0, 0), (-1, 0), 8.5),
                ("ROWBACKGROUNDS",(0, 1), (-1, -1), [_ROW_A, _ROW_B]),
                ("GRID",          (0, 0), (-1, -1), 0.3, _SLATE),
                ("FONTSIZE",      (0, 1), (-1, -1), 8.5),
                ("LEFTPADDING",   (0, 0), (-1, -1), 5),
                ("RIGHTPADDING",  (0, 0), (-1, -1), 5),
                ("TOPPADDING",    (0, 0), (-1, -1), 3),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
                ("VALIGN",        (0, 0), (-1, -1), "MIDDLE"),
            ])

        curr  = profile.get("currency", "")
        name  = profile.get("name", ticker)
        story = []

        # ── Title ──────────────────────────────────────────────────────────
        story.append(Paragraph("Equity Research Report", S_TITLE))
        story.append(Paragraph(f"{name}  ({ticker})", S_H1))
        story.append(Paragraph(
            f"Sector: {profile.get('sector','N/A')}  ·  Industry: {profile.get('industry','N/A')}  "
            f"·  Country: {profile.get('country','N/A')}  ·  Generated: {datetime.now().strftime('%Y-%m-%d')}",
            S_CAPTION,
        ))
        story.append(HRFlowable(width="100%", thickness=1, color=_INDIGO, spaceAfter=8))

        # ── Company Description ───────────────────────────────────────────
        desc = profile.get("description", "")
        if desc:
            story.append(Paragraph("Company Overview", S_H2))
            story.append(Paragraph(desc, S_BODY))

        # ── Key Metrics Table ─────────────────────────────────────────────
        story.append(Paragraph("Key Metrics", S_H2))

        def _v(val, fmt="{}", fallback="N/A"):
            try:
                return fmt.format(float(val)) if val is not None else fallback
            except (TypeError, ValueError):
                return fallback

        price  = metrics.get("price")
        chg    = metrics.get("change_pct")
        pe_t   = metrics.get("pe_trailing")
        pe_f   = metrics.get("pe_forward")
        eps_t  = metrics.get("eps_trailing")
        ev_eb  = metrics.get("ev_ebitda")
        pb     = metrics.get("price_to_book")
        ps     = metrics.get("price_to_sales")
        dy     = metrics.get("div_yield")
        beta   = metrics.get("beta")

        mdata = [
            ["Metric", "Value", "Metric", "Value"],
            ["Price",       f"{curr} {price:,.2f}" if price else "N/A",   "Market Cap",   metrics.get("market_cap_fmt","N/A")],
            ["Change",      f"{chg:+.2f}%" if chg is not None else "N/A", "P/E (TTM)",    f"{pe_t:.1f}×" if pe_t else "N/A"],
            ["P/E (Fwd)",   f"{pe_f:.1f}×" if pe_f else "N/A",            "EV/EBITDA",    f"{ev_eb:.1f}×" if ev_eb else "N/A"],
            ["P/B",         f"{pb:.2f}×"if pb   else "N/A",            "P/S",          f"{ps:.2f}×" if ps else "N/A"],
            ["EPS (TTM)",   f"{curr} {eps_t:.2f}" if eps_t else "N/A",    "Div Yield",    f"{dy*100:.2f}%" if dy else "—"],
            ["Beta",        f"{beta:.2f}"if beta else "N/A",            "52W Range",    f"{metrics.get('52w_low','?')} – {metrics.get('52w_high','?')}"],
        ]
        cw = [3.5*cm, 3.5*cm, 3.5*cm, 3.5*cm]
        t  = Table(mdata, colWidths=cw)
        t.setStyle(_tbl_style())
        story.append(t)
        story.append(Spacer(1, 6))

        # ── Analyst Consensus ─────────────────────────────────────────────
        story.append(Paragraph("Analyst Consensus", S_H2))
        rec = analyst.get("recommendation", "N/A")
        tm  = analyst.get("target_mean")
        th  = analyst.get("target_high")
        tl  = analyst.get("target_low")
        nb  = analyst.get("nb_analysts")
        adata = [
            ["Recommendation", "Target Mean", "Target High", "Target Low", "# Analysts"],
            [
                rec,
                f"{curr} {tm:,.2f}" if tm else "N/A",
                f"{curr} {th:,.2f}" if th else "N/A",
                f"{curr} {tl:,.2f}" if tl else "N/A",
                str(nb) if nb else "N/A",
            ],
        ]
        ta = Table(adata, colWidths=[3*cm]*5)
        ta.setStyle(_tbl_style())
        story.append(ta)
        story.append(Spacer(1, 6))

        # ── Investment Thesis ─────────────────────────────────────────────
        story.append(Paragraph("Investment Thesis", S_H2))
        tp = pitch.get("target_price")
        up = pitch.get("upside")
        story.append(Paragraph(
            f"<b>Recommendation:</b> {rec}  ·  "
            f"<b>Target Price:</b> {curr} {tp:,.2f}  ·  " if tp else f"<b>Recommendation:</b> {rec}  ·  ",
            S_BODY,
        ))
        if up is not None:
            story.append(Paragraph(f"<b>Implied Upside:</b> {up:+.1f}%  ({pitch.get('target_method','')})", S_BODY))
        story.append(Spacer(1, 4))

        story.append(Paragraph("<b>Bull Case</b>", S_BODY))
        for b in pitch.get("thesis_bullets", []):
            story.append(Paragraph(f"PASS  {b}", S_BULLET))
        story.append(Spacer(1, 4))

        story.append(Paragraph("<b>Key Risks</b>", S_BODY))
        for r in pitch.get("risk_bullets", []):
            story.append(Paragraph(f"▲  {r}", S_BULLET))

        # ── Sentiment & News ──────────────────────────────────────────────
        story.append(HRFlowable(width="100%", thickness=0.5, color=_SLATE, spaceAfter=4, spaceBefore=10))
        story.append(Paragraph("Market Sentiment & Recent News", S_H2))
        story.append(Paragraph(
            f"Overall Sentiment: <b>{sentiment.get('label','N/A')}</b>  "
            f"(Score: {sentiment.get('score','N/A')}/100  ·  "
            f"Bullish signals: {sentiment.get('bull',0)}  ·  Bearish signals: {sentiment.get('bear',0)})",
            S_BODY,
        ))
        story.append(Spacer(1, 4))
        for i, item in enumerate(news, 1):
            title  = item.get("title", "N/A")[:120]
            source = item.get("publisher", "N/A")
            try:
                dt_str = datetime.fromtimestamp(item.get("providerPublishTime", 0)).strftime("%Y-%m-%d")
            except Exception:
                dt_str = "N/A"
            story.append(Paragraph(f"<b>{i}. {title}</b>", S_BODY))
            story.append(Paragraph(f"{source}  ·  {dt_str}", S_CAPTION))

        # ── Footer ────────────────────────────────────────────────────────
        story.append(Spacer(1, 16))
        story.append(HRFlowable(width="100%", thickness=0.5, color=_SLATE))
        story.append(Paragraph(
            "Generated by Ravinala v2.0  ·  TSIVAHINY Matthias  ·  "
            "For informational purposes only — not financial advice.  "
            "Data sourced via yfinance.",
            S_CAPTION,
        ))

        doc.build(story)
        buf.seek(0)
        return buf.read()

    except ImportError:
        return None
    except Exception:
        return None


# ─────────────────────────────────────────────────────────────────────────────
# 6. STREAMLIT TAB RENDERER
# ─────────────────────────────────────────────────────────────────────────────

# Plotly theme constants (match Ravinala dark palette)
_BG     = "#07080d"
_GRID   = "rgba(255,255,255,0.04)"
_FONT   = "#9ca3af"
_ACCENT = "#6366f1"
_GREEN  = "#10b981"
_RED    = "#ef4444"
_AMBER  = "#f59e0b"
_MUTED  = "#94a3b8"


def _base_layout(**kw) -> Dict:
    return dict(
        paper_bgcolor=_BG,
        plot_bgcolor=_BG,
        font=dict(color=_FONT, family="Inter, SF Pro Display, sans-serif"),
        margin=dict(l=0, r=0, t=32, b=0),
        xaxis=dict(gridcolor=_GRID),
        yaxis=dict(gridcolor=_GRID),
        legend=dict(bgcolor="rgba(0,0,0,0)", bordercolor="rgba(0,0,0,0)"),
        **kw,
    )


def render_equity_research_tab() -> None:
    """Entry point called from app.py to render the full Equity Research tab."""
    import streamlit as st
    import plotly.graph_objects as go
    from plotly.subplots import make_subplots

    st.markdown("## Equity Research")
    st.markdown("*One-click fundamental report: valuation comps, performance, sentiment & investment pitch*")

    # ── Top 20 Most-Researched Equities ───────────────────────────────────────
    with st.expander("**Top 20 Most-Researched Equities** (Market Leaders)", expanded=False):
        st.caption("Click any ticker below to instantly load research. Updated quarterly based on institutional coverage.")

        # Format table for display
        display_df = TOP_20_EQUITIES.copy()
        display_df["P/E"] = display_df["P/E"].apply(lambda x: f"{x:.1f}×")
        display_df["Market Cap"] = display_df["Market Cap ($T)"].apply(lambda x: f"${x:.2f}T")
        display_df = display_df[["Ticker", "Company", "Sector", "P/E", "Market Cap", "Coverage"]]

        # Styled dataframe
        def highlight_row(row):
            return ["background-color: rgba(99,102,241,0.12); font-weight: 600"] * len(row)

        st.dataframe(
            display_df.style.apply(highlight_row, axis=1),
            width="stretch",
            hide_index=True,
        )

        # Quick-select buttons (organized by sector)
        st.markdown("##### Quick Select by Sector")

        sectors_quick = {
            "Technology": ["AAPL", "MSFT", "NVDA", "GOOGL", "INTC", "AMD"],
            "Financials": ["JPM", "V", "MA", "BAC", "GS"],
            "Energy": ["XOM", "CVX"],
            "Consumer": ["TSLA", "AMZN", "WMT"],
            "Healthcare": ["JNJ", "UNH"],
            "Media": ["NFLX", "META", "DIS"],
        }

        cols = st.columns(len(sectors_quick))
        for col_idx, (sector_label, tickers) in enumerate(sectors_quick.items()):
            with cols[col_idx]:
                st.markdown(f"**{sector_label}**")
                for t in tickers:
                    if st.button(t, key=f"eq_quick_{t}", width="stretch"):
                        st.session_state["er_ticker_val"] = t
                        st.rerun()

    # ── Input row ─────────────────────────────────────────────────────────────
    ci1, ci2, ci3 = st.columns([2, 1, 1])
    with ci1:
        er_ticker = st.text_input(
            "Ticker Symbol",
            value=st.session_state.get("er_ticker_val", "AAPL"),
            placeholder="NVDA, MC.PA, ASML.AS, MSFT…",
            key="er_ticker_input",
        )
    with ci2:
        er_period = st.selectbox(
            "Performance Window", ["3mo", "6mo", "1y", "2y", "3y"], index=2, key="er_period",
        )
    with ci3:
        st.markdown("<div style='padding-top:28px'></div>", unsafe_allow_html=True)
        er_btn = st.button("Analyse", key="er_analyse_btn", width="stretch")

    if er_btn and er_ticker.strip():
        clean = er_ticker.upper().strip()
        st.session_state["er_ticker_val"] = clean
        # Clear old results so the spinner shows
        st.session_state.pop("er_data", None)
        st.session_state.pop("er_engine", None)
        with st.spinner(f"Fetching data for {clean}…"):
            _engine = EquityResearchEngine(clean)
            _base   = _engine.fetch_all()
        if _base["error"]:
            st.error(_base["error"])
            return
        st.session_state["er_data"]   = _base
        st.session_state["er_engine"] = clean

    # Gate: wait for data
    if "er_data" not in st.session_state:
        st.info("Enter a ticker and click ** Analyse** to generate a full research report.")
        return

    data    = st.session_state["er_data"]
    ticker  = st.session_state["er_engine"]
    engine  = EquityResearchEngine(ticker)

    profile = data["profile"]
    metrics = data["metrics"]
    analyst = data["analyst"]
    news    = data["news"]
    period  = st.session_state.get("er_period", "1y")

    # ── Header ────────────────────────────────────────────────────────────────
    st.markdown(
        f"""<div style="margin:16px 0 8px">
          <span style="font-size:1.55rem;font-weight:700;color:#f1f2f6">{profile['name']}</span>
          <span style="margin-left:12px;font-size:0.85rem;color:#818cf8;
                       background:rgba(99,102,241,0.13);padding:2px 10px;border-radius:20px">
            {profile['sector']}
          </span>
          <span style="margin-left:8px;font-size:0.85rem;color:#9ca3af">{profile['industry']}</span>
        </div>""",
        unsafe_allow_html=True,
    )
    if profile.get("description"):
        with st.expander("Company Overview", expanded=False):
            st.caption(profile["description"])
            if profile.get("website"):
                st.markdown(f"[{profile['website']}]({profile['website']})")
            if profile.get("employees"):
                st.caption(f"Full-time employees: {profile['employees']:,}")

    # ── Key Metrics row ───────────────────────────────────────────────────────
    price  = metrics.get("price")
    chg    = metrics.get("change_pct")
    curr   = profile.get("currency", "")
    c1, c2, c3, c4, c5, c6 = st.columns(6)
    with c1:
        chg_str = f"{chg:+.2f}%" if chg is not None else None
        st.metric("Price", f"{price:,.2f} {curr}" if price else "N/A", chg_str)
    with c2:
        st.metric("Market Cap", metrics.get("market_cap_fmt", "N/A"))
    with c3:
        pe = metrics.get("pe_trailing")
        st.metric("P/E (TTM)", f"{pe:.1f}×" if pe else "N/A")
    with c4:
        eps = metrics.get("eps_trailing")
        st.metric("EPS (TTM)", f"{eps:.2f}" if eps else "N/A")
    with c5:
        dy = metrics.get("div_yield")
        st.metric("Div Yield", f"{dy*100:.2f}%" if dy else "—")
    with c6:
        beta = metrics.get("beta")
        st.metric("Beta", f"{beta:.2f}" if beta else "N/A")

    st.divider()

    # ── Inner tabs ────────────────────────────────────────────────────────────
    tabs = st.tabs(["Performance", "Valuation", "Financials", "Sentiment", "The Pitch"])

    # ════════════ TAB 1 — PERFORMANCE ════════════════════════════════════════
    with tabs[0]:
        st.markdown("#### Relative Performance")
        with st.spinner("Loading price history…"):
            hist_s             = engine.get_price_history(period)
            hist_b, _, blabel  = engine.get_benchmark_history(period)

        if hist_s is None or hist_s.empty:
            st.warning("Price history not available for this ticker.")
        else:
            s_norm = hist_s["Close"] / hist_s["Close"].iloc[0] * 100
            fig    = go.Figure()
            fig.add_trace(go.Scatter(
                x=s_norm.index, y=s_norm.values, mode="lines", name=ticker,
                line=dict(color=_ACCENT, width=2.2),
            ))
            if hist_b is not None and not hist_b.empty:
                b_norm = hist_b["Close"] / hist_b["Close"].iloc[0] * 100
                fig.add_trace(go.Scatter(
                    x=b_norm.index, y=b_norm.values, mode="lines", name=blabel,
                    line=dict(color=_MUTED, width=1.5, dash="dot"),
                ))
            fig.add_hline(y=100, line_dash="dash", line_color="rgba(255,255,255,0.1)")
            fig.update_layout(**_base_layout(height=400, hovermode="x unified",
                                             yaxis_title="Indexed Return (base=100)"))
            st.plotly_chart(fig, width="stretch")

            # Stats
            cs1, cs2, cs3, cs4 = st.columns(4)
            ret_s  = float(s_norm.iloc[-1] - 100)
            ret_b  = float(b_norm.iloc[-1] - 100) if (hist_b is not None and not hist_b.empty) else None
            vol_a  = float(hist_s["Close"].pct_change().dropna().std() * np.sqrt(252) * 100)
            with cs1:
                st.metric(f"{ticker} Return", f"{ret_s:+.1f}%")
            with cs2:
                if ret_b is not None:
                    st.metric(blabel, f"{ret_b:+.1f}%", f"α {ret_s - ret_b:+.1f}%")
            with cs3:
                st.metric("Annualized Vol", f"{vol_a:.1f}%")
            with cs4:
                hi = metrics.get("52w_high")
                lo = metrics.get("52w_low")
                if hi and lo:
                    st.metric("52W Range", f"{lo:,.2f} – {hi:,.2f}")

    # ════════════ TAB 2 — VALUATION / COMPS ══════════════════════════════════
    with tabs[1]:
        st.markdown("#### Valuation Multiples & Peer Comparison")
        st.caption("Peer group auto-selected by GICS sector · Data via yfinance")

        with st.spinner("Fetching peer multiples (may take ~10 s)…"):
            df_peers = engine.get_peer_multiples()

        if df_peers.empty:
            st.warning("Peer data unavailable.")
        else:
            # Highlight main row
            def _hl(row):
                color = "background-color:rgba(99,102,241,0.18);font-weight:600" if row.name == ticker else ""
                return [color] * len(row)

            num_cols = ["P/E (TTM)", "P/E (Fwd)", "EV/EBITDA", "P/S", "P/B"]
            fmt_map  = {c: "{:.1f}" for c in num_cols if c in df_peers.columns}
            st.dataframe(
                df_peers.style.apply(_hl, axis=1).format(formatter=fmt_map, na_rep="—"),
                width="stretch",
            )

            # Grouped bar chart
            plot_cols = [c for c in num_cols if c in df_peers.columns]
            if plot_cols:
                pal = [_ACCENT, "#818cf8", "#a5b4fc", "#c7d2fe", "#e0e7ff", "#f0f4ff"]
                fig2 = go.Figure()
                for i, (idx_t, row) in enumerate(df_peers.iterrows()):
                    vals = [float(row[c]) if pd.notna(row.get(c)) else 0 for c in plot_cols]
                    fig2.add_trace(go.Bar(
                        name=str(idx_t), x=plot_cols, y=vals,
                        marker_color=pal[i % len(pal)],
                        opacity=1.0 if idx_t == ticker else 0.55,
                    ))
                fig2.update_layout(**_base_layout(height=360, barmode="group"))
                st.plotly_chart(fig2, width="stretch")

        # Individual multiples detail
        st.markdown("##### Key Multiples")
        mv1, mv2, mv3, mv4 = st.columns(4)
        with mv1: st.metric("P/E (TTM)",   f"{metrics.get('pe_trailing'):.1f}×"if metrics.get("pe_trailing")   else "—")
        with mv2: st.metric("EV/EBITDA",   f"{metrics.get('ev_ebitda'):.1f}×"if metrics.get("ev_ebitda")     else "—")
        with mv3: st.metric("Price/Sales", f"{metrics.get('price_to_sales'):.2f}×" if metrics.get("price_to_sales") else "—")
        with mv4: st.metric("Price/Book",  f"{metrics.get('price_to_book'):.2f}×"if metrics.get("price_to_book")  else "—")

    # ════════════ TAB 3 — FINANCIALS ═════════════════════════════════════════
    with tabs[2]:
        st.markdown("#### Financial Health — Last 4 Fiscal Years")
        with st.spinner("Loading financial statements…"):
            fin = engine.get_financials()

        if not fin["years"]:
            st.warning("Financial statements not available for this ticker.")
        else:
            def _bn(v): return v / 1e9

            fig3 = make_subplots(
                rows=1, cols=2,
                subplot_titles=["Revenue ($B)", "Net Income ($B)"],
                horizontal_spacing=0.08,
            )
            fig3.add_trace(go.Bar(
                x=fin["years"], y=[_bn(v) for v in fin["revenue"]],
                marker_color=_ACCENT, name="Revenue",
            ), row=1, col=1)
            ni_colors = [_GREEN if v >= 0 else _RED for v in fin["net_income"]]
            fig3.add_trace(go.Bar(
                x=fin["years"], y=[_bn(v) for v in fin["net_income"]],
                marker_color=ni_colors, name="Net Income",
            ), row=1, col=2)
            fig3.update_layout(
                paper_bgcolor=_BG, plot_bgcolor=_BG, font=dict(color=_FONT),
                height=360, showlegend=False, margin=dict(l=0, r=0, t=40, b=0),
            )
            for col_i in [1, 2]:
                fig3.update_xaxes(gridcolor=_GRID, row=1, col=col_i)
                fig3.update_yaxes(gridcolor=_GRID, row=1, col=col_i)
            st.plotly_chart(fig3, width="stretch")

            # Growth KPIs
            gm1, gm2, gm3, gm4 = st.columns(4)
            rg  = metrics.get("revenue_growth")
            eg  = metrics.get("earnings_growth")
            pm  = metrics.get("profit_margin")
            roe = metrics.get("roe")
            with gm1: st.metric("Revenue Growth (YoY)", f"{rg*100:+.1f}%" if rg is not None else "—")
            with gm2: st.metric("Earnings Growth (YoY)", f"{eg*100:+.1f}%" if eg is not None else "—")
            with gm3: st.metric("Net Profit Margin",    f"{pm*100:.1f}%"if pm is not None else "—")
            with gm4: st.metric("Return on Equity",     f"{roe*100:.1f}%"if roe is not None else "—")

    # ════════════ TAB 4 — SENTIMENT & NEWS ═══════════════════════════════════
    with tabs[3]:
        st.markdown("#### Market Sentiment & Latest News")
        if not news:
            st.warning("No news found for this ticker.")
        else:
            sentiment = engine.score_sentiment(news)
            label     = sentiment["label"]
            score     = sentiment["score"]
            s_color   = _GREEN if label == "Bullish" else (_RED if label == "Bearish" else _AMBER)
            s_icon    = "" if label == "Bullish" else ("" if label == "Bearish" else "")

            sc1, sc2, sc3 = st.columns([1, 1, 2])
            with sc1:
                st.metric("Sentiment Signal", f"{s_icon} {label}")
            with sc2:
                st.metric("Score", f"{score}/100")
            with sc3:
                fig_g = go.Figure(go.Indicator(
                    mode="gauge+number", value=score,
                    gauge={
                        "axis":    {"range": [0, 100], "tickcolor": _FONT},
                        "bar":     {"color": s_color},
                        "bgcolor": "rgba(0,0,0,0)",
                        "steps":   [
                            {"range": [0,  35],  "color": "rgba(239,68,68,0.12)"},
                            {"range": [35, 65],  "color": "rgba(245,158,11,0.10)"},
                            {"range": [65, 100], "color": "rgba(16,185,129,0.12)"},
                        ],
                    },
                    number={"font": {"color": s_color, "size": 26}},
                    domain={"x": [0.1, 0.9], "y": [0, 1]},
                ))
                fig_g.update_layout(
                    paper_bgcolor=_BG, height=150,
                    margin=dict(l=10, r=10, t=10, b=10),
                    font=dict(color=_FONT),
                )
                st.plotly_chart(fig_g, width="stretch")

            st.markdown("---")
            for item in news:
                title  = item.get("title", "No title")
                source = item.get("publisher", "Unknown")
                url    = item.get("link", "#")
                try:
                    dt_str = datetime.fromtimestamp(item.get("providerPublishTime", 0)).strftime("%Y-%m-%d %H:%M")
                except Exception:
                    dt_str = "N/A"
                art_sent = engine.score_sentiment([item])
                art_icon = "" if art_sent["label"] == "Bullish" else ("" if art_sent["label"] == "Bearish" else "")
                with st.expander(f"{art_icon}  {title[:100]}"):
                    st.caption(f"**{source}**  ·  {dt_str}")
                    st.markdown(f"[Read full article →]({url})")

    # ════════════ TAB 5 — THE PITCH ══════════════════════════════════════════
    with tabs[4]:
        st.markdown("#### The Pitch — Investment Thesis")
        with st.spinner("Generating investment analysis…"):
            pitch = engine.generate_investment_pitch()

        rec    = pitch.get("recommendation", "N/A")
        tp     = pitch.get("target_price")
        upside = pitch.get("upside")
        rec_color = _GREEN if "BUY" in rec else (_RED if "SELL" in rec else _AMBER)

        tp1, tp2, tp3 = st.columns(3)
        with tp1:
            st.markdown(
                f"""<div style="padding:16px;border-radius:8px;
                             background:rgba(99,102,241,0.08);
                             border:1px solid rgba(99,102,241,0.2);text-align:center">
                  <div style="color:#9ca3af;font-size:0.72rem;text-transform:uppercase;
                              letter-spacing:0.06em">Analyst Recommendation</div>
                  <div style="font-size:1.5rem;font-weight:700;color:{rec_color};margin-top:4px">{rec}</div>
                </div>""",
                unsafe_allow_html=True,
            )
        with tp2:
            if tp:
                st.metric("Target Price", f"{curr} {tp:,.2f}", pitch.get("target_method", ""))
            else:
                st.metric("Target Price", "N/A")
        with tp3:
            if upside is not None:
                st.metric("Potential Upside", f"{upside:+.1f}%")
            else:
                st.metric("Potential Upside", "N/A")

        st.markdown("<div style='margin-top:16px'></div>", unsafe_allow_html=True)
        col_t, col_r = st.columns(2)
        with col_t:
            st.markdown("**Investment Thesis**")
            for b in pitch.get("thesis_bullets", []):
                st.markdown(f"PASS  {b}")
        with col_r:
            st.markdown("**Key Risks**")
            for r in pitch.get("risk_bullets", []):
                st.markdown(f"WARNING  {r}")

        # Analyst price-target range bar chart
        th = analyst.get("target_high")
        tl = analyst.get("target_low")
        tm = analyst.get("target_mean")
        cp = metrics.get("price")
        if th and tl and tm and cp:
            st.markdown("##### Analyst Price Target Range")
            mid_est = (tl + th) / 2
            fig_tp = go.Figure()
            fig_tp.add_trace(go.Bar(
                x=["Low Target", "Median Estimate", "Mean Target", "High Target", "Current Price"],
                y=[tl, mid_est, tm, th, cp],
                marker_color=[_RED, _AMBER, _ACCENT, _GREEN, _MUTED],
                text=[f"{v:,.2f}" for v in [tl, mid_est, tm, th, cp]],
                textposition="outside",
                textfont=dict(color=_FONT),
            ))
            fig_tp.add_hline(
                y=cp, line_dash="dash", line_color="rgba(255,255,255,0.2)",
                annotation_text=f"Current: {cp:,.2f}",
                annotation_font_color=_FONT,
            )
            fig_tp.update_layout(**_base_layout(height=340))
            st.plotly_chart(fig_tp, width="stretch")

        nb = analyst.get("nb_analysts")
        if nb:
            st.caption(f"Based on {nb} analyst{'s' if nb != 1 else ''} · {pitch.get('target_method','')}")

    # ── PDF Export ────────────────────────────────────────────────────────────
    st.divider()
    if st.button("Export Research Report (PDF)", key="er_pdf_btn"):
        with st.spinner("Generating PDF…"):
            sentiment_for_pdf = engine.score_sentiment(news)
            pitch_for_pdf     = engine.generate_investment_pitch()
            pdf_bytes = generate_equity_report_pdf(
                ticker=ticker,
                profile=profile,
                metrics=metrics,
                analyst=analyst,
                pitch=pitch_for_pdf,
                news=news,
                sentiment=sentiment_for_pdf,
            )
        if pdf_bytes:
            st.download_button(
                label="Download PDF",
                data=pdf_bytes,
                file_name=f"{ticker}_equity_research_{datetime.now().strftime('%Y%m%d')}.pdf",
                mime="application/pdf",
                key="er_pdf_dl",
            )
        else:
            st.error("PDF generation failed — ensure reportlab is installed (`pip install reportlab`).")
