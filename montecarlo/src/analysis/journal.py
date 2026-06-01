"""
journal.py — Trade journal with analytics (P&L, win rate, expectancy).
"""
from __future__ import annotations

from dataclasses import dataclass, field, asdict
from datetime import datetime
from typing import Dict, List, Optional

import numpy as np
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import streamlit as st

from .core import DARK_THEME

_C = DARK_THEME


@dataclass
class JournalEntry:
    entry_id: str
    symbol: str
    direction: str              # 'Long' | 'Short'
    entry_date: str
    entry_price: float
    exit_date: Optional[str]
    exit_price: Optional[float]
    shares: float
    strategy: str
    setup: str                  # e.g., 'Breakout', 'Mean Reversion', 'Trend Follow'
    timeframe: str
    emotion: str                # 'Confident' | 'Neutral' | 'Fearful' | 'FOMO'
    rating: int                 # 1–5 process quality rating
    notes: str
    tags: List[str]
    pnl: float = 0.0
    pnl_pct: float = 0.0
    status: str = "open"        # 'open' | 'closed'

    def __post_init__(self):
        if self.exit_price and self.entry_price and self.shares:
            self.pnl = (self.exit_price - self.entry_price) * self.shares
            if self.direction == "Short":
                self.pnl = -self.pnl
            self.pnl_pct = (self.pnl / (self.entry_price * self.shares)) * 100
            self.status = "closed"

    def to_dict(self) -> Dict:
        return asdict(self)


class TradeJournal:
    """Persistent trade journal with analytics dashboard."""

    STATE_KEY = "fa_journal_v2"

    def __init__(self):
        if self.STATE_KEY not in st.session_state:
            st.session_state[self.STATE_KEY] = []

    @property
    def entries(self) -> List[Dict]:
        return st.session_state.get(self.STATE_KEY, [])

    def add_entry(self, entry: JournalEntry) -> None:
        entries = self.entries.copy()
        entries.append(entry.to_dict())
        st.session_state[self.STATE_KEY] = entries

    def remove_entry(self, entry_id: str) -> None:
        st.session_state[self.STATE_KEY] = [
            e for e in self.entries if e["entry_id"] != entry_id
        ]

    def update_entry(self, entry_id: str, updates: Dict) -> None:
        entries = self.entries.copy()
        for e in entries:
            if e["entry_id"] == entry_id:
                e.update(updates)
                # Recompute P&L if prices updated
                if "exit_price" in updates and e.get("entry_price") and e.get("shares"):
                    ep, xp, sh = e["entry_price"], e["exit_price"], e["shares"]
                    pnl = (xp - ep) * sh
                    if e.get("direction") == "Short":
                        pnl = -pnl
                    e["pnl"] = round(pnl, 2)
                    e["pnl_pct"] = round(pnl / (ep * sh) * 100, 2)
                    e["status"] = "closed"
        st.session_state[self.STATE_KEY] = entries

    # ─────────────────────────────────────────────────────────────────────────
    # ANALYTICS
    # ─────────────────────────────────────────────────────────────────────────

    def get_analytics(self) -> Dict:
        """Compute performance analytics from closed trades."""
        closed = [e for e in self.entries if e.get("status") == "closed"]
        if not closed:
            return {}

        pnls = [e.get("pnl", 0) for e in closed]
        pnl_pcts = [e.get("pnl_pct", 0) for e in closed]

        wins = [p for p in pnls if p > 0]
        losses = [p for p in pnls if p <= 0]

        win_rate = len(wins) / len(pnls) * 100 if pnls else 0
        avg_win = float(np.mean(wins)) if wins else 0
        avg_loss = abs(float(np.mean(losses))) if losses else 0
        expectancy = win_rate / 100 * avg_win - (1 - win_rate / 100) * avg_loss
        profit_factor = sum(wins) / max(abs(sum(losses)), 0.01)
        total_pnl = sum(pnls)

        # By strategy
        by_strategy: Dict[str, List[float]] = {}
        for e in closed:
            strat = e.get("strategy", "Unknown")
            by_strategy.setdefault(strat, []).append(e.get("pnl", 0))

        strat_stats = {
            k: {
                "n_trades": len(v),
                "total_pnl": round(sum(v), 2),
                "win_rate":  round(sum(1 for p in v if p > 0) / len(v) * 100, 1),
                "avg_pnl":   round(float(np.mean(v)), 2),
            }
            for k, v in by_strategy.items()
        }

        # By symbol
        by_symbol: Dict[str, List[float]] = {}
        for e in closed:
            sym = e.get("symbol", "?")
            by_symbol.setdefault(sym, []).append(e.get("pnl", 0))

        # Streak analysis
        wins_series = [1 if p > 0 else 0 for p in pnls]
        max_win_streak = max_loss_streak = 0
        current_streak = streak_type = 0
        for w in wins_series:
            if w == 1:
                current_streak = current_streak + 1 if streak_type == 1 else 1
                streak_type = 1
                max_win_streak = max(max_win_streak, current_streak)
            else:
                current_streak = current_streak + 1 if streak_type == 0 else 1
                streak_type = 0
                max_loss_streak = max(max_loss_streak, current_streak)

        return {
            "n_trades":         len(closed),
            "total_pnl":        round(total_pnl, 2),
            "win_rate":         round(win_rate, 1),
            "avg_win":          round(avg_win, 2),
            "avg_loss":         round(avg_loss, 2),
            "expectancy":       round(expectancy, 2),
            "profit_factor":    round(profit_factor, 2),
            "best_trade":       round(max(pnls), 2),
            "worst_trade":      round(min(pnls), 2),
            "max_win_streak":   max_win_streak,
            "max_loss_streak":  max_loss_streak,
            "avg_pnl_pct":      round(float(np.mean(pnl_pcts)), 2),
            "by_strategy":      strat_stats,
        }

    def render_analytics_chart(self) -> go.Figure:
        """Render cumulative P&L and win/loss distribution."""
        closed = [e for e in self.entries if e.get("status") == "closed"]
        if not closed:
            return go.Figure()

        pnls = [e.get("pnl", 0) for e in closed]
        cum_pnl = np.cumsum(pnls)

        fig = make_subplots(
            rows=1, cols=2,
            subplot_titles=["Cumulative P&L", "P&L Distribution"],
        )

        # Cumulative P&L
        colors = [_C["green"] if v > 0 else _C["red"] for v in cum_pnl]
        fig.add_trace(go.Scatter(
            x=list(range(1, len(cum_pnl) + 1)),
            y=cum_pnl.tolist(),
            mode="lines+markers",
            line=dict(color=_C["blue"], width=2),
            marker=dict(color=colors, size=6),
            name="Cumulative P&L",
        ), row=1, col=1)
        fig.add_hline(y=0, row=1, col=1,
                      line=dict(color=_C["border"], width=1, dash="dash"))

        # Distribution
        fig.add_trace(go.Histogram(
            x=pnls,
            name="P&L",
            marker_color=[_C["green"] if p > 0 else _C["red"] for p in pnls],
            nbinsx=20,
            opacity=0.75,
        ), row=1, col=2)

        fig.update_layout(
            paper_bgcolor=_C["bg"],
            plot_bgcolor=_C["panel"],
            font=dict(color=_C["text"]),
            title="<b>Trade Journal Analytics</b>",
            height=380,
            showlegend=False,
            xaxis=dict(gridcolor=_C["border"]),
            yaxis=dict(gridcolor=_C["border"]),
            xaxis2=dict(gridcolor=_C["border"]),
            yaxis2=dict(gridcolor=_C["border"]),
        )
        return fig

    def to_dataframe(self) -> pd.DataFrame:
        """Export all entries as a DataFrame."""
        if not self.entries:
            return pd.DataFrame()
        df = pd.DataFrame(self.entries)
        cols = ["symbol", "direction", "entry_date", "entry_price", "exit_date",
                "exit_price", "shares", "pnl", "pnl_pct", "strategy", "setup",
                "rating", "status", "notes"]
        cols = [c for c in cols if c in df.columns]
        return df[cols]
